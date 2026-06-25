import os
from functools import wraps
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import ProtectedError
from .models import (
    Estabelecimento, EstabelecimentoUsuario, CategoriaCusto,
    CaracteristicaAtendimento, CaracteristicaAtendimentoOpcao, Custo, Cliente,
    Atendimento, Pagamento, AtendimentoCaracteristica, FormaPagamento,
)
from braid_system.security.models.usuario import Usuario
from .access import is_admin, get_estabelecimento_ativo


# Apenas o papel 'admin' é administrador para fins de isolamento de dados.
# (O papel 'consultor' NÃO é exceção: vê somente estabelecimentos vinculados.)
TIPOS_ADMIN = ('admin',)


def admin_required(view_func):
    """
    Restringe o acesso à área de administrador.

    Exige usuário autenticado E com papel administrativo (apenas admin).
    Quem não está logado vai para a tela de login; quem está logado mas não tem
    permissão é redirecionado para a gestão com uma mensagem.
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Faça login para acessar a administração.')
            return redirect('home')
        if not is_admin(request.user):
            messages.error(request, 'Acesso restrito à área de administrador.')
            return redirect('gestao')
        return view_func(request, *args, **kwargs)
    return _wrapped


def home(request):
    return render(request, 'core/home.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('gestao')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
            return redirect('home')
    return redirect('home')


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def gestao(request):
    return render(request, 'core/gestao.html')


def perfil(request):
    if not request.user.is_authenticated:
        return redirect('home')

    if is_admin(request.user):
        # Admin pode operar sobre qualquer estabelecimento.
        estabelecimentos_usuario = list(Estabelecimento.objects.order_by('nome'))
    else:
        vinculos = (
            EstabelecimentoUsuario.objects
            .filter(usuario=request.user)
            .select_related('estabelecimento')
            .order_by('estabelecimento__nome')
        )
        estabelecimentos_usuario = [v.estabelecimento for v in vinculos]

    if request.method == 'POST':
        est_id = request.POST.get('estabelecimento_id', '').strip()
        ids_validos = [str(e.pk) for e in estabelecimentos_usuario]
        if est_id in ids_validos:
            request.session['estabelecimento_ativo_id'] = est_id
            messages.success(request, 'Estabelecimento atualizado.')
        else:
            messages.error(request, 'Estabelecimento inválido.')
        return redirect('perfil')

    return render(request, 'core/perfil.html', {
        'estabelecimentos_usuario': estabelecimentos_usuario,
    })


def admin_painel(request):
    return render(request, 'core/admin_painel.html')


def cadastro_estabelecimento(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if not nome:
            messages.error(request, 'Informe o nome do estabelecimento.')
        else:
            Estabelecimento.objects.create(nome=nome)
            messages.success(request, f'"{nome}" cadastrado com sucesso!')
            return redirect('cadastro_estabelecimento')
    return render(request, 'core/cadastro_estabelecimento.html')


# ── Estabelecimentos ───────────────────────────────────────────────────────────

def _ctx_estabelecimentos(editando=None):
    return {
        'estabelecimentos': Estabelecimento.objects.order_by('nome'),
        'total_estabelecimentos': Estabelecimento.objects.count(),
        'editando': editando,
    }


def estabelecimentos(request):
    return render(request, 'core/estabelecimentos.html', _ctx_estabelecimentos())


def estabelecimento_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            Estabelecimento.objects.create(nome=nome)
            messages.success(request, f'Estabelecimento "{nome}" criado com sucesso!')
            return redirect('estabelecimentos')
    return render(request, 'core/estabelecimentos.html', _ctx_estabelecimentos())


def estabelecimento_editar(request, pk):
    est = get_object_or_404(Estabelecimento, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            est.nome = nome
            est.save()
            messages.success(request, f'Estabelecimento "{nome}" atualizado.')
            return redirect('estabelecimentos')
    return render(request, 'core/estabelecimentos.html', _ctx_estabelecimentos(editando=est))


def estabelecimento_excluir(request, pk):
    est = get_object_or_404(Estabelecimento, pk=pk)
    if request.method == 'POST':
        nome = est.nome
        est.delete()
        messages.success(request, f'Estabelecimento "{nome}" excluído.')
    return redirect('estabelecimentos')


# ── Categorias de Custo ────────────────────────────────────────────────────

def _ctx_categorias(editando=None):
    """Contexto base para as views de categorias."""
    raiz = CategoriaCusto.objects.filter(
        nivel_superior__isnull=True
    ).prefetch_related('subcategorias').order_by('nome')
    return {
        'categorias_raiz': raiz,
        'total_categorias': CategoriaCusto.objects.count(),
        'editando': editando,
    }


def categorias_custo(request):
    return render(request, 'core/categorias_custo.html', _ctx_categorias())


def _salvar_ilustracao(request, atual='', pasta='categorias_custo'):
    """
    Resolve o valor final do campo ilustracao.
    Prioridade: arquivo enviado > texto digitado > valor atual.
    Retorna string (URL relativa ou emoji/texto).
    """
    arquivo = request.FILES.get('ilustracao_arquivo')
    if arquivo:
        caminho = default_storage.save(
            os.path.join(pasta, arquivo.name),
            arquivo,
        )
        # URL resolvida pelo storage ativo: caminho local em desenvolvimento
        # (FileSystemStorage) ou URL pública do Supabase em produção (S3).
        return default_storage.url(caminho)
    texto = request.POST.get('ilustracao', '').strip()
    if texto:
        return texto
    return atual


def categoria_custo_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        ilustracao = _salvar_ilustracao(request)
        pai_id = request.POST.get('nivel_superior') or None

        vinculado_atendimento = request.POST.get('vinculado_atendimento') == 'on'

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            pai = get_object_or_404(CategoriaCusto, pk=pai_id) if pai_id else None
            CategoriaCusto.objects.create(
                nome=nome, ilustracao=ilustracao,
                nivel_superior=pai, vinculado_atendimento=vinculado_atendimento,
            )
            messages.success(request, f'Categoria "{nome}" criada com sucesso!')
            return redirect('categorias_custo')

    return render(request, 'core/categorias_custo.html', _ctx_categorias())


def categoria_custo_editar(request, pk):
    categoria = get_object_or_404(CategoriaCusto, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        ilustracao = _salvar_ilustracao(request, atual=categoria.ilustracao)
        pai_id = request.POST.get('nivel_superior') or None

        vinculado_atendimento = request.POST.get('vinculado_atendimento') == 'on'

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            pai = None
            if pai_id and str(pai_id) != str(pk):
                pai = get_object_or_404(CategoriaCusto, pk=pai_id)

            categoria.nome = nome
            categoria.ilustracao = ilustracao
            categoria.nivel_superior = pai
            categoria.vinculado_atendimento = vinculado_atendimento
            categoria.save()
            messages.success(request, f'Categoria "{nome}" atualizada.')
            return redirect('categorias_custo')

    return render(request, 'core/categorias_custo.html', _ctx_categorias(editando=categoria))


def categoria_custo_excluir(request, pk):
    categoria = get_object_or_404(CategoriaCusto, pk=pk)
    if request.method == 'POST':
        nome = categoria.nome
        categoria.delete()
        messages.success(request, f'Categoria "{nome}" excluída.')
    return redirect('categorias_custo')


# ── Características de Atendimento ────────────────────────────────────────────

def _ctx_caracteristicas(editando=None):
    return {
        'caracteristicas': CaracteristicaAtendimento.objects.prefetch_related('opcoes').order_by('ordem'),
        'total_caracteristicas': CaracteristicaAtendimento.objects.count(),
        'editando': editando,
    }


def caracteristicas_atendimento(request):
    return render(request, 'core/caracteristicas_atendimento.html', _ctx_caracteristicas())


def caracteristica_atendimento_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        pergunta = request.POST.get('pergunta', '').strip()
        ordem = request.POST.get('ordem', '').strip()
        numero_maximo_selecao = request.POST.get('numero_maximo_selecao', '1').strip()
        contem_dado_sensivel = request.POST.get('contem_dado_sensivel') == 'on'

        if not nome or not pergunta or not ordem:
            messages.error(request, 'Nome, pergunta e ordem são obrigatórios.')
        else:
            CaracteristicaAtendimento.objects.create(
                nome=nome,
                pergunta=pergunta,
                ordem=int(ordem),
                numero_maximo_selecao=int(numero_maximo_selecao),
                contem_dado_sensivel=contem_dado_sensivel,
            )
            messages.success(request, f'Característica "{nome}" criada com sucesso!')
            return redirect('caracteristicas_atendimento')

    return render(request, 'core/caracteristicas_atendimento.html', _ctx_caracteristicas())


def caracteristica_atendimento_editar(request, pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        pergunta = request.POST.get('pergunta', '').strip()
        ordem = request.POST.get('ordem', '').strip()
        numero_maximo_selecao = request.POST.get('numero_maximo_selecao', '1').strip()
        contem_dado_sensivel = request.POST.get('contem_dado_sensivel') == 'on'

        if not nome or not pergunta or not ordem:
            messages.error(request, 'Nome, pergunta e ordem são obrigatórios.')
        else:
            caracteristica.nome = nome
            caracteristica.pergunta = pergunta
            caracteristica.ordem = int(ordem)
            caracteristica.numero_maximo_selecao = int(numero_maximo_selecao)
            caracteristica.contem_dado_sensivel = contem_dado_sensivel
            caracteristica.save()
            messages.success(request, f'Característica "{nome}" atualizada.')
            return redirect('caracteristicas_atendimento')

    return render(request, 'core/caracteristicas_atendimento.html', _ctx_caracteristicas(editando=caracteristica))


def caracteristica_atendimento_excluir(request, pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)
    if request.method == 'POST':
        nome = caracteristica.nome
        caracteristica.delete()
        messages.success(request, f'Característica "{nome}" excluída.')
    return redirect('caracteristicas_atendimento')


def _ctx_opcoes(caracteristica, editando=None, pre_selecionado=None):
    opcoes_raiz = (
        CaracteristicaAtendimentoOpcao.objects
        .filter(caracteristica_atendimento=caracteristica, nivel_superior__isnull=True)
        .prefetch_related('subdivisoes')
        .order_by('nome')
    )
    return {
        'caracteristica': caracteristica,
        'opcoes_raiz': opcoes_raiz,
        'total_opcoes': CaracteristicaAtendimentoOpcao.objects.filter(caracteristica_atendimento=caracteristica).count(),
        'editando': editando,
        'pre_selecionado': pre_selecionado,
    }


def caracteristica_atendimento_opcoes(request, pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)
    return render(request, 'core/opcoes_caracteristica_atendimento.html', _ctx_opcoes(caracteristica))


def opcao_caracteristica_criar(request, pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        ilustracao = _salvar_ilustracao(request, pasta='opcoes_caracteristica')
        nivel_superior_id = request.POST.get('nivel_superior') or None

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            nivel_superior = None
            if nivel_superior_id:
                nivel_superior = get_object_or_404(
                    CaracteristicaAtendimentoOpcao,
                    pk=nivel_superior_id,
                    caracteristica_atendimento=caracteristica,
                )
            CaracteristicaAtendimentoOpcao.objects.create(
                caracteristica_atendimento=caracteristica,
                nome=nome,
                ilustracao=ilustracao,
                nivel_superior=nivel_superior,
            )
            messages.success(request, f'Opção "{nome}" criada com sucesso!')
            return redirect('caracteristica_atendimento_opcoes', pk=pk)

    return render(request, 'core/opcoes_caracteristica_atendimento.html', _ctx_opcoes(caracteristica))


def opcao_caracteristica_editar(request, pk, opcao_pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)
    opcao = get_object_or_404(CaracteristicaAtendimentoOpcao, pk=opcao_pk, caracteristica_atendimento=caracteristica)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        ilustracao = _salvar_ilustracao(request, atual=opcao.ilustracao, pasta='opcoes_caracteristica')
        nivel_superior_id = request.POST.get('nivel_superior') or None

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            nivel_superior = None
            if nivel_superior_id and str(nivel_superior_id) != str(opcao_pk):
                nivel_superior = get_object_or_404(
                    CaracteristicaAtendimentoOpcao,
                    pk=nivel_superior_id,
                    caracteristica_atendimento=caracteristica,
                )
            opcao.nome = nome
            opcao.ilustracao = ilustracao
            opcao.nivel_superior = nivel_superior
            opcao.save()
            messages.success(request, f'Opção "{nome}" atualizada.')
            return redirect('caracteristica_atendimento_opcoes', pk=pk)

    return render(request, 'core/opcoes_caracteristica_atendimento.html',
                  _ctx_opcoes(caracteristica, editando=opcao))


def opcao_caracteristica_excluir(request, pk, opcao_pk):
    caracteristica = get_object_or_404(CaracteristicaAtendimento, pk=pk)
    opcao = get_object_or_404(CaracteristicaAtendimentoOpcao, pk=opcao_pk, caracteristica_atendimento=caracteristica)
    if request.method == 'POST':
        nome = opcao.nome
        opcao.delete()
        messages.success(request, f'Opção "{nome}" excluída.')
    return redirect('caracteristica_atendimento_opcoes', pk=pk)


# ── Usuários ───────────────────────────────────────────────────────────────────

def _ctx_usuarios(editando=None):
    return {
        'usuarios': Usuario.objects.order_by('nome'),
        'total_usuarios': Usuario.objects.count(),
        'editando': editando,
    }


def usuarios(request):
    return render(request, 'core/usuarios.html', _ctx_usuarios())


def usuario_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        email = request.POST.get('email', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        password = request.POST.get('password', '')

        if not nome or not email or not tipo or not password:
            messages.error(request, 'Todos os campos são obrigatórios.')
        elif Usuario.objects.filter(email=email).exists():
            messages.error(request, f'Já existe um usuário com o e-mail "{email}".')
        else:
            Usuario.objects.create_user(email=email, nome=nome, password=password, tipo=tipo)
            messages.success(request, f'Usuário "{nome}" criado com sucesso!')
            return redirect('usuarios')

    return render(request, 'core/usuarios.html', _ctx_usuarios())


def usuario_editar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        tipo = request.POST.get('tipo', '').strip()
        ativo = request.POST.get('ativo', '1') == '1'

        if not nome or not tipo:
            messages.error(request, 'Nome e tipo são obrigatórios.')
        else:
            usuario.nome = nome
            usuario.tipo = tipo
            usuario.ativo = ativo
            usuario.save()
            messages.success(request, f'Usuário "{nome}" atualizado.')
            return redirect('usuarios')

    return render(request, 'core/usuarios.html', _ctx_usuarios(editando=usuario))


def usuario_excluir(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        nome = usuario.nome
        usuario.delete()
        messages.success(request, f'Usuário "{nome}" excluído.')
    return redirect('usuarios')


# ── Acessos de usuários a estabelecimentos ────────────────────────────────────

def _ctx_acessos(request, editando=None):
    filtro_est = request.GET.get('estabelecimento', '')
    filtro_usr = request.GET.get('usuario', '')

    qs = EstabelecimentoUsuario.objects.select_related(
        'usuario', 'estabelecimento', 'incluido_por'
    ).order_by('estabelecimento__nome', 'usuario__nome')

    if filtro_est:
        qs = qs.filter(estabelecimento_id=filtro_est)
    if filtro_usr:
        qs = qs.filter(usuario_id=filtro_usr)

    return {
        'acessos': qs,
        'total_acessos': qs.count(),
        'usuarios': Usuario.objects.filter(ativo=True).order_by('nome'),
        'estabelecimentos': Estabelecimento.objects.order_by('nome'),
        'editando': editando,
        'filtro_estabelecimento': filtro_est,
        'filtro_usuario': filtro_usr,
    }


def acessos_estabelecimento(request):
    return render(request, 'core/acessos_estabelecimento.html', _ctx_acessos(request))


def acesso_criar(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario', '').strip()
        estabelecimento_id = request.POST.get('estabelecimento', '').strip()
        tipo_acesso = request.POST.get('tipo_acesso', '').strip()

        if not usuario_id or not estabelecimento_id or not tipo_acesso:
            messages.error(request, 'Todos os campos são obrigatórios.')
        elif EstabelecimentoUsuario.objects.filter(
            usuario_id=usuario_id, estabelecimento_id=estabelecimento_id
        ).exists():
            messages.error(request, 'Este usuário já possui acesso a esse estabelecimento.')
        else:
            usuario = get_object_or_404(Usuario, pk=usuario_id)
            estabelecimento = get_object_or_404(Estabelecimento, pk=estabelecimento_id)
            EstabelecimentoUsuario.objects.create(
                usuario=usuario,
                estabelecimento=estabelecimento,
                tipo_acesso=tipo_acesso,
                incluido_por=request.user if request.user.is_authenticated else None,
            )
            messages.success(
                request,
                f'Acesso de "{usuario.nome}" ao estabelecimento "{estabelecimento.nome}" criado.'
            )
            return redirect('acessos_estabelecimento')

    return render(request, 'core/acessos_estabelecimento.html', _ctx_acessos(request))


def acesso_editar(request, pk):
    acesso = get_object_or_404(EstabelecimentoUsuario, pk=pk)

    if request.method == 'POST':
        tipo_acesso = request.POST.get('tipo_acesso', '').strip()
        if not tipo_acesso:
            messages.error(request, 'Selecione um nível de acesso.')
        else:
            acesso.tipo_acesso = tipo_acesso
            acesso.save()
            messages.success(
                request,
                f'Acesso de "{acesso.usuario.nome}" atualizado para "{acesso.get_tipo_acesso_display()}".'
            )
            return redirect('acessos_estabelecimento')

    return render(request, 'core/acessos_estabelecimento.html', _ctx_acessos(request, editando=acesso))


def acesso_excluir(request, pk):
    acesso = get_object_or_404(EstabelecimentoUsuario, pk=pk)
    if request.method == 'POST':
        nome_usuario = acesso.usuario.nome
        nome_est = acesso.estabelecimento.nome
        acesso.delete()
        messages.success(request, f'Acesso de "{nome_usuario}" ao "{nome_est}" removido.')
    return redirect('acessos_estabelecimento')


# ── Formas de Pagamento ──────────────────────────────────────────────────────

def _ctx_formas_pagamento(editando=None):
    formas = FormaPagamento.objects.order_by('-padrao', 'nome')
    return {
        'formas_pagamento': formas,
        'total_formas': formas.count(),
        'editando': editando,
    }


def formas_pagamento(request):
    return render(request, 'core/formas_pagamento.html', _ctx_formas_pagamento())


def forma_pagamento_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        padrao = request.POST.get('padrao') == 'on'
        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            FormaPagamento.objects.create(nome=nome, padrao=padrao)
            messages.success(request, f'Forma de pagamento "{nome}" criada com sucesso!')
            return redirect('formas_pagamento')
    return render(request, 'core/formas_pagamento.html', _ctx_formas_pagamento())


def forma_pagamento_editar(request, pk):
    forma = get_object_or_404(FormaPagamento, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        padrao = request.POST.get('padrao') == 'on'
        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            forma.nome = nome
            forma.padrao = padrao
            forma.save()
            messages.success(request, f'Forma de pagamento "{nome}" atualizada.')
            return redirect('formas_pagamento')
    return render(request, 'core/formas_pagamento.html', _ctx_formas_pagamento(editando=forma))


def forma_pagamento_excluir(request, pk):
    forma = get_object_or_404(FormaPagamento, pk=pk)
    if request.method == 'POST':
        nome = forma.nome
        try:
            forma.delete()
            messages.success(request, f'Forma de pagamento "{nome}" excluída.')
        except ProtectedError:
            messages.error(
                request,
                f'Não é possível excluir "{nome}": há pagamentos vinculados a esta forma.',
            )
    return redirect('formas_pagamento')


# ── Módulos principais ─────────────────────────────────────────────────────────

def _fmt_duracao(minutos):
    """Formata minutos em 'Hh MMmin' / 'HH:MM' amigável."""
    if not minutos:
        return ''
    h, m = divmod(int(minutos), 60)
    if h and m:
        return f'{h}h{m:02d}'
    if h:
        return f'{h}h'
    return f'{m}min'


def _parse_hora(valor):
    """Aceita 'HH:MM' ou 'HH:MM:SS' e retorna datetime.time."""
    valor = (valor or '').strip()
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(valor, fmt).time()
        except ValueError:
            continue
    return None


def _duracao_para_minutos(valor):
    """Converte 'HH:MM' em minutos inteiros. Retorna None se vazio/invalido."""
    valor = (valor or '').strip()
    if not valor:
        return None
    try:
        partes = valor.split(':')
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
        total = h * 60 + m
        return total or None
    except (ValueError, IndexError):
        return None


def _parse_dinheiro(raw):
    """Converte texto monetario em Decimal. Aceita '120.50', '120,50' e '1.234,56'."""
    raw = (raw or '').strip()
    if not raw:
        return None
    if ',' in raw and '.' in raw:
        # Formato BR: ponto de milhar, virgula decimal
        raw = raw.replace('.', '').replace(',', '.')
    elif ',' in raw:
        raw = raw.replace(',', '.')
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _ctx_atendimentos(request, editando=None, mes=None, ano=None):
    from datetime import date as date_cls
    estabelecimento = _get_estabelecimento_ativo(request)

    hoje = date_cls.today()
    ano = ano or hoje.year
    mes = mes or hoje.month

    MESES_PT = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    MESES_PT_FULL = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                     'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    meses = []
    for delta in range(-6, 7):
        m = mes + delta
        y = ano
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        meses.append({'mes': m, 'ano': y, 'label': f"{MESES_PT[m]}/{str(y)[2:]}"})

    atendimentos_lista = []
    clientes_qs = Cliente.objects.none()
    duracoes_sugeridas = []

    if estabelecimento:
        clientes_qs = (
            Cliente.objects
            .filter(estabelecimento=estabelecimento, anonimizado=False)
            .order_by('apelido', 'data_cadastro')
        )

        qs = (
            Atendimento.objects
            .filter(estabelecimento=estabelecimento, data__year=ano, data__month=mes)
            .select_related('cliente')
            .prefetch_related('pagamentos', 'caracteristicas__opcao__nivel_superior', 'custos')
            .order_by('-data', '-hora')
        )
        for at in qs:
            at.total_pago = sum((p.valor for p in at.pagamentos.all()), Decimal('0'))
            at.duracao_fmt = _fmt_duracao(at.duracao)
            at.caracteristica_nomes = [
                f"{ac.opcao.nivel_superior.nome} › {ac.opcao.nome}" if ac.opcao.nivel_superior else ac.opcao.nome
                for ac in at.caracteristicas.all()
            ]
            at.custos_total = sum((c.valor for c in at.custos.all()), Decimal('0'))
            atendimentos_lista.append(at)

        # Sugestoes de duracao a partir de atendimentos anteriores
        minutos_distintos = (
            Atendimento.objects
            .filter(estabelecimento=estabelecimento, duracao__isnull=False)
            .values_list('duracao', flat=True)
            .distinct()
        )
        for mins in sorted({m for m in minutos_distintos if m}):
            duracoes_sugeridas.append({
                'min': mins,
                'valor': f'{mins // 60:02d}:{mins % 60:02d}',
                'label': _fmt_duracao(mins),
            })

    # Caracteristicas (ordenadas) com todas as opcoes para o wizard
    caracteristicas = (
        CaracteristicaAtendimento.objects
        .prefetch_related('opcoes')
        .order_by('ordem')
    )

    # Categorias de custo vinculadas a atendimento (uma etapa por categoria)
    categorias_vinculadas = (
        CategoriaCusto.objects
        .filter(vinculado_atendimento=True)
        .order_by('nome')
    )

    # Formas de pagamento (a padrao vem primeiro para pre-selecao no wizard)
    formas_pagamento = FormaPagamento.objects.order_by('-padrao', 'nome')

    # Atributos calculados para o formulario de edicao
    if editando is not None:
        editando.total_pago = sum(
            (p.valor for p in editando.pagamentos.all()), Decimal('0'),
        )
        editando.duracao_edit = (
            f'{editando.duracao // 60:02d}:{editando.duracao % 60:02d}'
            if editando.duracao else ''
        )

    agora = datetime.now()
    return {
        'atendimentos': atendimentos_lista,
        'total_atendimentos': len(atendimentos_lista),
        'clientes': clientes_qs,
        'caracteristicas': caracteristicas,
        'categorias_vinculadas': categorias_vinculadas,
        'formas_pagamento': formas_pagamento,
        'duracoes_sugeridas': duracoes_sugeridas,
        'editando': editando,
        'hoje': agora.strftime('%Y-%m-%d'),
        'agora': agora.strftime('%H:%M'),
        'mes_ativo': mes,
        'ano_ativo': ano,
        'meses': meses,
        'mes_label': f"{MESES_PT_FULL[mes]} de {ano}",
    }


def atendimentos(request):
    if not request.user.is_authenticated:
        return redirect('home')
    mes = int(request.GET.get('mes') or 0) or None
    ano = int(request.GET.get('ano') or 0) or None
    return render(request, 'core/atendimentos.html', _ctx_atendimentos(request, mes=mes, ano=ano))


def atendimento_verificar(request):
    """Verifica (AJAX) se cliente já foi atendido na data informada."""
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'auth'}, status=403)
    estabelecimento = _get_estabelecimento_ativo(request)
    cliente_id = request.GET.get('cliente_id', '').strip()
    data_str = request.GET.get('data', '').strip()
    if not estabelecimento or not cliente_id or not data_str:
        return JsonResponse({'duplicata': False})
    try:
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'duplicata': False})
    duplicata = Atendimento.objects.filter(
        estabelecimento=estabelecimento,
        cliente_id=cliente_id,
        data=data_obj,
    ).exists()
    return JsonResponse({'duplicata': duplicata})


def atendimento_criar(request):
    if not request.user.is_authenticated:
        return redirect('home')
    if request.method != 'POST':
        return redirect('atendimentos')

    estabelecimento = _get_estabelecimento_ativo(request)
    if not estabelecimento:
        messages.error(request, 'Selecione um estabelecimento no perfil antes de registrar atendimentos.')
        return redirect('atendimentos')

    cliente_id = request.POST.get('cliente_id', '').strip()
    novo_cliente = request.POST.get('novo_cliente', '').strip()
    data_val = request.POST.get('data', '').strip()
    hora_val = request.POST.get('hora', '').strip()
    duracao_val = request.POST.get('duracao', '').strip()
    forma_pagamento_id = request.POST.get('forma_pagamento_id', '').strip()
    opcoes_ids = request.POST.getlist('opcoes')

    # Validacao dos campos obrigatorios
    erros = []
    if not cliente_id and not novo_cliente:
        erros.append('Informe o cliente do atendimento.')
    if not data_val:
        erros.append('A data do atendimento é obrigatória.')
    hora_obj = _parse_hora(hora_val)
    if not hora_obj:
        erros.append('A hora do atendimento é obrigatória.')
    try:
        data_obj = datetime.strptime(data_val, '%Y-%m-%d').date()
    except ValueError:
        data_obj = None
        if data_val:
            erros.append('Data inválida.')
    pagamento_dec = _parse_dinheiro(request.POST.get('pagamento_valor', ''))
    if pagamento_dec is None or pagamento_dec < 0:
        pagamento_dec = None
        erros.append('Informe o valor total recebido pelo serviço.')

    # Data não pode ser futura
    if data_obj and data_obj > datetime.today().date():
        erros.append('Não é possível registrar atendimentos com data futura.')

    # Mesmo cliente não pode ter mais de um atendimento no mesmo dia
    if data_obj and cliente_id and not erros:
        ja_atendido = Atendimento.objects.filter(
            estabelecimento=estabelecimento,
            cliente_id=cliente_id,
            data=data_obj,
        ).exists()
        if ja_atendido:
            erros.append('Este cliente já possui um atendimento registrado nesta data.')

    if erros:
        for e in erros:
            messages.error(request, e)
        return redirect('atendimentos')

    try:
        with transaction.atomic():
            # Cliente: existente ou novo (apenas pelo apelido)
            if cliente_id:
                cliente = get_object_or_404(Cliente, pk=cliente_id, estabelecimento=estabelecimento)
            else:
                cliente = Cliente.objects.create(
                    estabelecimento=estabelecimento,
                    apelido=novo_cliente,
                )

            atendimento = Atendimento.objects.create(
                estabelecimento=estabelecimento,
                cliente=cliente,
                data=data_obj,
                hora=hora_obj,
                duracao=_duracao_para_minutos(duracao_val),
            )

            # Forma de pagamento: a selecionada ou, na ausencia, a padrao
            forma_pagamento = None
            if forma_pagamento_id:
                forma_pagamento = FormaPagamento.objects.filter(pk=forma_pagamento_id).first()
            if forma_pagamento is None:
                forma_pagamento = FormaPagamento.objects.filter(padrao=True).first()

            # Pagamento vinculado ao atendimento
            Pagamento.objects.create(
                atendimento=atendimento,
                forma_pagamento=forma_pagamento,
                valor=pagamento_dec,
            )

            # Caracteristicas selecionadas (opcoes em qualquer nivel)
            opcoes = CaracteristicaAtendimentoOpcao.objects.filter(pk__in=opcoes_ids)
            for opcao in opcoes:
                AtendimentoCaracteristica.objects.get_or_create(
                    atendimento=atendimento, opcao=opcao,
                )

            # Custos relacionados (uma etapa por categoria vinculada)
            for chave, bruto in request.POST.items():
                if not chave.startswith('custo_'):
                    continue
                valor_custo = _parse_dinheiro(bruto)
                if valor_custo is None or valor_custo <= 0:
                    continue
                cat_id = chave[len('custo_'):]
                categoria = CategoriaCusto.objects.filter(
                    pk=cat_id, vinculado_atendimento=True, nivel_superior__isnull=False,
                ).first()
                if not categoria:
                    continue
                Custo.objects.create(
                    estabelecimento=estabelecimento,
                    categoria_custo=categoria,
                    atendimento=atendimento,
                    descricao=categoria.nome,
                    data=data_obj,
                    valor=valor_custo,
                )

        messages.success(request, f'Atendimento de "{cliente.apelido}" registrado com sucesso!')
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f'Erro ao registrar atendimento: {exc}')

    mes = int(request.POST.get('mes', 0)) or None
    ano = int(request.POST.get('ano', 0)) or None
    return redirect(f'/atendimentos/?mes={mes or ""}&ano={ano or ""}')


def atendimento_editar(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    estabelecimento = _get_estabelecimento_ativo(request)
    atendimento = get_object_or_404(Atendimento, pk=pk, estabelecimento=estabelecimento)
    mes = int(request.GET.get('mes', atendimento.data.month))
    ano = int(request.GET.get('ano', atendimento.data.year))

    if request.method == 'POST':
        mes = int(request.POST.get('mes', mes))
        ano = int(request.POST.get('ano', ano))
        cliente_id = request.POST.get('cliente_id', '').strip()
        data_val = request.POST.get('data', '').strip()
        hora_val = request.POST.get('hora', '').strip()
        duracao_val = request.POST.get('duracao', '').strip()

        erros = []
        hora_obj = _parse_hora(hora_val)
        if not hora_obj:
            erros.append('A hora é obrigatória.')
        try:
            data_obj = datetime.strptime(data_val, '%Y-%m-%d').date()
        except ValueError:
            data_obj = None
            erros.append('Data inválida.')
        pagamento_dec = _parse_dinheiro(request.POST.get('pagamento_valor', ''))

        if not erros:
            try:
                with transaction.atomic():
                    if cliente_id:
                        atendimento.cliente = get_object_or_404(
                            Cliente, pk=cliente_id, estabelecimento=estabelecimento,
                        )
                    atendimento.data = data_obj
                    atendimento.hora = hora_obj
                    atendimento.duracao = _duracao_para_minutos(duracao_val)
                    atendimento.save()

                    if pagamento_dec is not None:
                        pagamento = atendimento.pagamentos.first()
                        if pagamento:
                            pagamento.valor = pagamento_dec
                            pagamento.save()
                        else:
                            Pagamento.objects.create(
                                atendimento=atendimento,
                                forma_pagamento=None,
                                valor=pagamento_dec,
                            )
                messages.success(request, 'Atendimento atualizado.')
                return redirect(f'/atendimentos/?mes={mes}&ano={ano}')
            except Exception as exc:  # noqa: BLE001
                messages.error(request, f'Erro ao atualizar: {exc}')
        else:
            for e in erros:
                messages.error(request, e)

    return render(request, 'core/atendimentos.html', _ctx_atendimentos(request, editando=atendimento, mes=mes, ano=ano))


def atendimento_excluir(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    estabelecimento = _get_estabelecimento_ativo(request)
    atendimento = get_object_or_404(Atendimento, pk=pk, estabelecimento=estabelecimento)
    mes = atendimento.data.month
    ano = atendimento.data.year
    if request.method == 'POST':
        atendimento.delete()
        messages.success(request, 'Atendimento removido.')
    return redirect(f'/atendimentos/?mes={mes}&ano={ano}')


def _get_estabelecimento_ativo(request):
    """Estabelecimento ativo da sessão, já validado contra o vínculo do usuário.

    Delegado a access.get_estabelecimento_ativo: usuários não-admin só obtêm
    estabelecimentos aos quais estão vinculados; o admin obtém qualquer um.
    """
    return get_estabelecimento_ativo(request)


def _ctx_custos(request, editando=None, mes=None, ano=None):
    from datetime import date, datetime
    import calendar

    estabelecimento = _get_estabelecimento_ativo(request)
    hoje = date.today()
    ano = ano or hoje.year
    mes = mes or hoje.month

    meses = []
    for delta in range(-6, 7):
        m = mes + delta
        y = ano
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        MESES_PT = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        meses.append({'mes': m, 'ano': y, 'label': f"{MESES_PT[m]}/{str(y)[2:]}"})

    qs = Custo.objects.none()
    total_mes = 0
    categorias = CategoriaCusto.objects.order_by('nome')
    subcategorias = CategoriaCusto.objects.filter(nivel_superior__isnull=False).order_by('nome')

    if estabelecimento:
        qs = (
            Custo.objects
            .filter(
                estabelecimento=estabelecimento,
                atendimento__isnull=True,
                data__year=ano,
                data__month=mes,
            )
            .select_related('categoria_custo')
            .order_by('-data', 'descricao')
        )
        total_mes = sum(c.valor for c in qs)

    return {
        'custos': qs,
        'editando': editando,
        'hoje': hoje.strftime('%Y-%m-%d'),
        'mes_ativo': mes,
        'ano_ativo': ano,
        'meses': meses,
        'total_mes': total_mes,
        'categorias': categorias,
        'subcategorias': subcategorias,
        'mes_label': ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                      'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'][mes] + f' de {ano}',
    }


def custos(request):
    if not request.user.is_authenticated:
        return redirect('home')
    mes = int(request.GET.get('mes') or 0) or None
    ano = int(request.GET.get('ano') or 0) or None
    return render(request, 'core/custos.html', _ctx_custos(request, mes=mes, ano=ano))


def custo_criar(request):
    if not request.user.is_authenticated:
        return redirect('home')
    mes = int(request.POST.get('mes', 0)) or None
    ano = int(request.POST.get('ano', 0)) or None

    if request.method == 'POST':
        estabelecimento = _get_estabelecimento_ativo(request)
        if not estabelecimento:
            messages.error(request, 'Selecione um estabelecimento no perfil antes de lançar custos.')
            return redirect('custos')

        categoria_id = request.POST.get('categoria_custo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        data_val = request.POST.get('data', '').strip()
        valor = request.POST.get('valor', '').strip().replace(',', '.')

        erros = []
        if not categoria_id:
            erros.append('Categoria é obrigatória.')
        if not data_val:
            erros.append('Data é obrigatória.')
        if not valor:
            erros.append('Valor é obrigatório.')

        if not erros:
            try:
                categoria = CategoriaCusto.objects.get(pk=categoria_id, vinculado_atendimento=False)
                if categoria.nivel_superior_id is None:
                    messages.error(request, 'Não é permitido vincular uma super categoria a um custo. Selecione uma subcategoria.')
                else:
                    Custo.objects.create(
                        estabelecimento=estabelecimento,
                        categoria_custo=categoria,
                        descricao=descricao,
                        data=data_val,
                        valor=valor,
                        atendimento=None,
                    )
                    messages.success(request, 'Custo lançado com sucesso.')
            except CategoriaCusto.DoesNotExist:
                messages.error(request, 'Categoria inválida.')
            except Exception as exc:
                messages.error(request, f'Erro ao salvar: {exc}')
        else:
            for e in erros:
                messages.error(request, e)

    return redirect(f'/custos/?mes={mes or ""}&ano={ano or ""}')


def custo_editar(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    custo = get_object_or_404(
        Custo, pk=pk, atendimento__isnull=True,
        estabelecimento=_get_estabelecimento_ativo(request),
    )
    mes = int(request.GET.get('mes', custo.data.month))
    ano = int(request.GET.get('ano', custo.data.year))

    if request.method == 'POST':
        mes = int(request.POST.get('mes', mes))
        ano = int(request.POST.get('ano', ano))
        categoria_id = request.POST.get('categoria_custo', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        data_val = request.POST.get('data', '').strip()
        valor = request.POST.get('valor', '').strip().replace(',', '.')

        try:
            categoria = CategoriaCusto.objects.get(pk=categoria_id, vinculado_atendimento=False)
            if categoria.nivel_superior_id is None:
                messages.error(request, 'Não é permitido vincular uma super categoria a um custo. Selecione uma subcategoria.')
            else:
                custo.categoria_custo = categoria
                custo.descricao = descricao
                custo.data = data_val
                custo.valor = valor
                custo.save()
                messages.success(request, 'Custo atualizado.')
        except Exception as exc:
            messages.error(request, f'Erro: {exc}')
        return redirect(f'/custos/?mes={mes}&ano={ano}')

    ctx = _ctx_custos(request, editando=custo, mes=mes, ano=ano)
    return render(request, 'core/custos.html', ctx)


def custo_excluir(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    custo = get_object_or_404(
        Custo, pk=pk, atendimento__isnull=True,
        estabelecimento=_get_estabelecimento_ativo(request),
    )
    mes = custo.data.month
    ano = custo.data.year
    if request.method == 'POST':
        custo.delete()
        messages.success(request, 'Custo removido.')
    return redirect(f'/custos/?mes={mes}&ano={ano}')


def _dias_label(dias):
    """Retorna texto amigável para 'tempo desde o último atendimento'."""
    if dias == 0:
        return 'hoje'
    if dias == 1:
        return 'ontem'
    if dias < 7:
        return f'há {dias} dias'
    if dias < 30:
        semanas = dias // 7
        return f'há {semanas} semanas' if semanas > 1 else 'há 1 semana'
    if dias < 365:
        meses = round(dias / 30)
        return f'há {meses} mes{"es" if meses > 1 else ""}'
    anos = round(dias / 365)
    return f'há {anos} ano{"s" if anos > 1 else ""}'


def _ctx_clientes(request, editando=None):
    from datetime import date as date_cls
    from django.db.models import Count, Max

    estabelecimento = _get_estabelecimento_ativo(request)
    clientes = []
    if estabelecimento:
        hoje = date_cls.today()
        qs = (
            Cliente.objects
            .filter(estabelecimento=estabelecimento, anonimizado=False)
            .annotate(
                total_atendimentos=Count('atendimentos'),
                ultimo_atendimento=Max('atendimentos__data'),
            )
            .order_by('apelido', 'data_cadastro')
        )
        clientes = list(qs)
        for c in clientes:
            if c.ultimo_atendimento:
                dias = (hoje - c.ultimo_atendimento).days
                c.dias_desde_ultimo = dias
                c.ultimo_label = _dias_label(dias)
            else:
                c.dias_desde_ultimo = None
                c.ultimo_label = None
    return {
        'clientes': clientes,
        'total_clientes': len(clientes),
        'editando': editando,
    }


def clientes(request):
    if not request.user.is_authenticated:
        return redirect('home')
    return render(request, 'core/clientes.html', _ctx_clientes(request))


def cliente_criar(request):
    if not request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        estabelecimento = _get_estabelecimento_ativo(request)
        if not estabelecimento:
            messages.error(request, 'Selecione um estabelecimento no perfil antes de cadastrar clientes.')
            return redirect('clientes')

        apelido = request.POST.get('apelido', '').strip()
        descricao = request.POST.get('descricao', '').strip()

        if not apelido:
            messages.error(request, 'O apelido/nome é obrigatório.')
        else:
            Cliente.objects.create(
                estabelecimento=estabelecimento,
                apelido=apelido,
                descricao=descricao,
            )
            messages.success(request, f'Cliente "{apelido}" cadastrado com sucesso!')
    return redirect('clientes')


def cliente_editar(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    cliente = get_object_or_404(
        Cliente, pk=pk, estabelecimento=_get_estabelecimento_ativo(request)
    )

    if request.method == 'POST':
        apelido = request.POST.get('apelido', '').strip()
        descricao = request.POST.get('descricao', '').strip()

        if not apelido:
            messages.error(request, 'O apelido/nome é obrigatório.')
        else:
            cliente.apelido = apelido
            cliente.descricao = descricao
            cliente.save()
            messages.success(request, f'Cliente "{apelido}" atualizado.')
            return redirect('clientes')

    return render(request, 'core/clientes.html', _ctx_clientes(request, editando=cliente))


def cliente_excluir(request, pk):
    if not request.user.is_authenticated:
        return redirect('home')
    cliente = get_object_or_404(
        Cliente, pk=pk, estabelecimento=_get_estabelecimento_ativo(request)
    )
    if request.method == 'POST':
        apelido = cliente.apelido
        cliente.delete()
        messages.success(request, f'Cliente "{apelido}" excluído.')
    return redirect('clientes')


def _fmt_money_br(valor):
    """Formata um Decimal/numero no padrao BR de milhar: 1.234,56 (sem prefixo)."""
    valor = Decimal(valor or 0).quantize(Decimal('0.01'))
    negativo = valor < 0
    inteiro, dec = f'{abs(valor):.2f}'.split('.')
    grupos = []
    while len(inteiro) > 3:
        grupos.insert(0, inteiro[-3:])
        inteiro = inteiro[:-3]
    grupos.insert(0, inteiro)
    texto = '.'.join(grupos) + ',' + dec
    return ('-' + texto) if negativo else texto


def _fmt_horas_br(total_min):
    """Converte minutos totais em 'Hh MMmin' amigavel."""
    total_min = int(total_min or 0)
    h, m = divmod(total_min, 60)
    if h and m:
        return f'{h}h{m:02d}'
    if h:
        return f'{h}h'
    if m:
        return f'{m}min'
    return '0h'


def relatorios(request):
    from datetime import date as date_cls
    from django.db.models import Sum, Count

    if not request.user.is_authenticated:
        return redirect('home')

    estabelecimento = _get_estabelecimento_ativo(request)

    MESES_PT = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    MESES_PT_FULL = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                     'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

    hoje = date_cls.today()
    relatorios_meses = []
    indice_inicial = 0

    if estabelecimento:
        # Conjunto de meses (ano, mes) que possuem atendimentos ou custos.
        chaves = set()
        for d in Atendimento.objects.filter(estabelecimento=estabelecimento).dates('data', 'month'):
            chaves.add((d.year, d.month))
        for d in Custo.objects.filter(estabelecimento=estabelecimento).dates('data', 'month'):
            chaves.add((d.year, d.month))
        chaves.add((hoje.year, hoje.month))  # garante o mes corrente no carrossel

        for ano, mes in sorted(chaves):
            at_agg = (
                Atendimento.objects
                .filter(estabelecimento=estabelecimento, data__year=ano, data__month=mes)
                .aggregate(qtd=Count('id'), minutos=Sum('duracao'))
            )
            total_atend = at_agg['qtd'] or 0
            total_min = at_agg['minutos'] or 0

            faturado = (
                Pagamento.objects
                .filter(
                    atendimento__estabelecimento=estabelecimento,
                    atendimento__data__year=ano,
                    atendimento__data__month=mes,
                )
                .aggregate(s=Sum('valor'))['s']
            ) or Decimal('0')

            # Total de custos = TODOS os custos do mes (avulsos + vinculados a atendimento)
            custos_total = (
                Custo.objects
                .filter(estabelecimento=estabelecimento, data__year=ano, data__month=mes)
                .aggregate(s=Sum('valor'))['s']
            ) or Decimal('0')

            lucro = faturado - custos_total
            horas_dec = (Decimal(total_min) / Decimal(60)) if total_min else Decimal('0')

            lucro_por_atend = (lucro / total_atend) if total_atend else None
            lucro_por_hora = (lucro / horas_dec) if horas_dec else None
            duracao_media_min = round(total_min / total_atend) if total_atend else None

            relatorios_meses.append({
                'ano': ano,
                'mes': mes,
                'label_curto': f'{MESES_PT[mes]}/{str(ano)[2:]}',
                'label_full': f'{MESES_PT_FULL[mes]} de {ano}',
                'total_atendimentos': total_atend,
                'duracao_media': _fmt_horas_br(duracao_media_min) if duracao_media_min is not None else None,
                'total_faturado': _fmt_money_br(faturado),
                'total_custos': _fmt_money_br(custos_total),
                'lucro_total': _fmt_money_br(lucro),
                'lucro_positivo': lucro >= 0,
                'lucro_por_atendimento': _fmt_money_br(lucro_por_atend) if lucro_por_atend is not None else None,
                'lucro_por_hora': _fmt_money_br(lucro_por_hora) if lucro_por_hora is not None else None,
            })

        # Foca o mes corrente; se nao houver, o ultimo (mais recente).
        indice_inicial = next(
            (i for i, m in enumerate(relatorios_meses)
             if m['ano'] == hoje.year and m['mes'] == hoje.month),
            len(relatorios_meses) - 1 if relatorios_meses else 0,
        )

    return render(request, 'core/relatorios.html', {
        'relatorios_meses': relatorios_meses,
        'indice_inicial': indice_inicial,
    })


# ── Proteção da área de administrador ────────────────────────────────────────
# Aplica login + verificação de papel (apenas admin) a todas as views do
# painel administrativo de forma centralizada — um único ponto de auditoria.
# Uma view nova de admin só fica protegida ao ser adicionada nesta lista.
_ADMIN_VIEWS = (
    'admin_painel',
    'estabelecimentos', 'estabelecimento_criar',
    'estabelecimento_editar', 'estabelecimento_excluir',
    'categorias_custo', 'categoria_custo_criar',
    'categoria_custo_editar', 'categoria_custo_excluir',
    'caracteristicas_atendimento', 'caracteristica_atendimento_criar',
    'caracteristica_atendimento_editar', 'caracteristica_atendimento_excluir',
    'caracteristica_atendimento_opcoes', 'opcao_caracteristica_criar',
    'opcao_caracteristica_editar', 'opcao_caracteristica_excluir',
    'usuarios', 'usuario_criar', 'usuario_editar', 'usuario_excluir',
    'acessos_estabelecimento', 'acesso_criar', 'acesso_editar', 'acesso_excluir',
    'formas_pagamento', 'forma_pagamento_criar',
    'forma_pagamento_editar', 'forma_pagamento_excluir',
)

for _view_name in _ADMIN_VIEWS:
    globals()[_view_name] = admin_required(globals()[_view_name])
