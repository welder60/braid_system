import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.files.storage import default_storage
from django.conf import settings
from .models import Estabelecimento, EstabelecimentoUsuario, CategoriaCusto, CaracteristicaAtendimento, CaracteristicaAtendimentoOpcao
from braid_system.security.models.usuario import Usuario


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


def gestao(request):
    return render(request, 'core/gestao.html')


def perfil(request):
    if not request.user.is_authenticated:
        return redirect('home')

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


def _salvar_ilustracao(request, atual=''):
    """
    Resolve o valor final do campo ilustracao.
    Prioridade: arquivo enviado > texto digitado > valor atual.
    Retorna string (URL relativa ou emoji/texto).
    """
    arquivo = request.FILES.get('ilustracao_arquivo')
    if arquivo:
        # Salva em media/categorias_custo/<nome_original>
        caminho = default_storage.save(
            os.path.join('categorias_custo', arquivo.name),
            arquivo,
        )
        return settings.MEDIA_URL + caminho
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
        ilustracao = request.POST.get('ilustracao', '').strip()
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
        ilustracao = request.POST.get('ilustracao', '').strip()
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
