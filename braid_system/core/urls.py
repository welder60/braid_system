from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('gestao/', views.gestao, name='gestao'),
    path('estabelecimentos/novo/', views.cadastro_estabelecimento, name='cadastro_estabelecimento'),
    path('admin-painel/', views.admin_painel, name='admin_painel'),
]
