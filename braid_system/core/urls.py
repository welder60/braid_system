from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('gestao/', views.gestao, name='gestao'),
    path('perfil/', views.perfil, name='perfil'),
    path('estabelecimentos/novo/', views.cadastro_estabelecimento, name='cadastro_estabelecimento'),

    # Estabelecimentos (admin CRUD)
    path('admin-painel/estabelecimentos/', views.estabelecimentos, name='estabelecimentos'),
    path('admin-painel/estabelecimentos/criar/', views.estabelecimento_criar, name='estabelecimento_criar'),
    path('admin-painel/estabelecimentos/<uuid:pk>/editar/', views.estabelecimento_editar, name='estabelecimento_editar'),
    path('admin-painel/estabelecimentos/<uuid:pk>/excluir/', views.estabelecimento_excluir, name='estabelecimento_excluir'),
    path('admin-painel/', views.admin_painel, name='admin_painel'),

    # Categorias de Custo
    path('admin-painel/categorias-custo/', views.categorias_custo, name='categorias_custo'),
    path('admin-painel/categorias-custo/criar/', views.categoria_custo_criar, name='categoria_custo_criar'),
    path('admin-painel/categorias-custo/<uuid:pk>/editar/', views.categoria_custo_editar, name='categoria_custo_editar'),
    path('admin-painel/categorias-custo/<uuid:pk>/excluir/', views.categoria_custo_excluir, name='categoria_custo_excluir'),

    # Características de Atendimento
    path('admin-painel/caracteristicas-atendimento/', views.caracteristicas_atendimento, name='caracteristicas_atendimento'),
    path('admin-painel/caracteristicas-atendimento/criar/', views.caracteristica_atendimento_criar, name='caracteristica_atendimento_criar'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/editar/', views.caracteristica_atendimento_editar, name='caracteristica_atendimento_editar'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/excluir/', views.caracteristica_atendimento_excluir, name='caracteristica_atendimento_excluir'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/', views.caracteristica_atendimento_opcoes, name='caracteristica_atendimento_opcoes'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/criar/', views.opcao_caracteristica_criar, name='opcao_caracteristica_criar'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/<uuid:opcao_pk>/editar/', views.opcao_caracteristica_editar, name='opcao_caracteristica_editar'),
    path('admin-painel/caracteristicas-atendimento/<uuid:pk>/opcoes/<uuid:opcao_pk>/excluir/', views.opcao_caracteristica_excluir, name='opcao_caracteristica_excluir'),
]
