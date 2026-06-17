from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('gestao/', views.gestao, name='gestao'),
    path('estabelecimentos/novo/', views.cadastro_estabelecimento, name='cadastro_estabelecimento'),
    path('admin-painel/', views.admin_painel, name='admin_painel'),

    # Categorias de Custo
    path('admin-painel/categorias-custo/', views.categorias_custo, name='categorias_custo'),
    path('admin-painel/categorias-custo/criar/', views.categoria_custo_criar, name='categoria_custo_criar'),
    path('admin-painel/categorias-custo/<uuid:pk>/editar/', views.categoria_custo_editar, name='categoria_custo_editar'),
    path('admin-painel/categorias-custo/<uuid:pk>/excluir/', views.categoria_custo_excluir, name='categoria_custo_excluir'),
]
