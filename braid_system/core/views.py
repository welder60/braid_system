from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Estabelecimento


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
