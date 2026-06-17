from django.urls import path
from . import views

urlpatterns = [
    path('estabelecimentos/novo/', views.cadastro_estabelecimento, name='cadastro_estabelecimento'),
]
