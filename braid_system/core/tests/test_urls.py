"""Resolucao e reverse das URLs nomeadas."""

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from braid_system.core import views


# ===========================================================================
# 6. Roteamento de URLs
# ===========================================================================
class UrlRoutingTests(SimpleTestCase):
    def test_reverse_nomes_principais(self):
        self.assertEqual(reverse("home"), "/")
        self.assertEqual(reverse("login"), "/login/")
        self.assertEqual(reverse("atendimentos"), "/atendimentos/")
        self.assertEqual(reverse("custos"), "/custos/")
        self.assertEqual(reverse("clientes"), "/clientes/")

    def test_resolve_aponta_para_view_correta(self):
        self.assertEqual(resolve("/").func, views.home)
        self.assertEqual(resolve("/gestao/").func, views.gestao)
        self.assertEqual(resolve("/atendimentos/criar/").func, views.atendimento_criar)
