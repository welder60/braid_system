import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.files.storage import default_storage
from django.conf import settings
from .models import Estabelecimento, CategoriaCusto


def home(request):
    return render(request, 'core/home.html')


def gestao(request):
    return render(request, 'core/gestao.html')


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

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            pai = get_object_or_404(CategoriaCusto, pk=pai_id) if pai_id else None
            CategoriaCusto.objects.create(nome=nome, ilustracao=ilustracao, nivel_superior=pai)
            messages.success(request, f'Categoria "{nome}" criada com sucesso!')
            return redirect('categorias_custo')

    return render(request, 'core/categorias_custo.html', _ctx_categorias())


def categoria_custo_editar(request, pk):
    categoria = get_object_or_404(CategoriaCusto, pk=pk)

    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        ilustracao = _salvar_ilustracao(request, atual=categoria.ilustracao)
        pai_id = request.POST.get('nivel_superior') or None

        if not nome:
            messages.error(request, 'O nome é obrigatório.')
        else:
            pai = None
            if pai_id and str(pai_id) != str(pk):
                pai = get_object_or_404(CategoriaCusto, pk=pai_id)

            categoria.nome = nome
            categoria.ilustracao = ilustracao
            categoria.nivel_superior = pai
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
