"""CRUD de clientes (multi-tenant)."""

from datetime import date

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import (
    Cliente,
)

from .utils import (
    HASHERS_RAPIDOS,
    AutenticadoComEstabelecimentoMixin,
    criar_atendimento,
    criar_estabelecimento,
)


# ===========================================================================
# 13. CRUD de clientes (multi-tenant)
# ===========================================================================
class ClienteViewTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("clientes")).status_code, 200)

    def test_criar(self):
        resp = self.client.post(
            reverse("cliente_criar"),
            {"apelido": "Dona Rita", "descricao": "Cliente fiel"},
        )
        self.assertRedirects(resp, reverse("clientes"))
        self.assertTrue(
            Cliente.objects.filter(
                apelido="Dona Rita", estabelecimento=self.est
            ).exists()
        )

    def test_criar_sem_apelido_nao_cria(self):
        resp = self.client.post(reverse("cliente_criar"), {"apelido": ""})
        self.assertRedirects(resp, reverse("clientes"))
        self.assertEqual(Cliente.objects.count(), 0)

    def test_criar_sem_estabelecimento_ativo(self):
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        resp = self.client.post(reverse("cliente_criar"), {"apelido": "X"})
        self.assertRedirects(resp, reverse("clientes"))
        self.assertEqual(Cliente.objects.count(), 0)

    def test_lista_isola_por_estabelecimento(self):
        outro = criar_estabelecimento("Outro")
        Cliente.objects.create(estabelecimento=outro, apelido="De Outro")
        Cliente.objects.create(estabelecimento=self.est, apelido="Meu")
        resp = self.client.get(reverse("clientes"))
        apelidos = {c.apelido for c in resp.context["clientes"]}
        self.assertEqual(apelidos, {"Meu"})

    def test_editar(self):
        c = Cliente.objects.create(estabelecimento=self.est, apelido="Velho")
        resp = self.client.post(
            reverse("cliente_editar", args=[c.pk]), {"apelido": "Novo"}
        )
        self.assertRedirects(resp, reverse("clientes"))
        c.refresh_from_db()
        self.assertEqual(c.apelido, "Novo")

    def test_excluir(self):
        c = Cliente.objects.create(estabelecimento=self.est, apelido="Del")
        resp = self.client.post(reverse("cliente_excluir", args=[c.pk]))
        self.assertRedirects(resp, reverse("clientes"))
        self.assertEqual(Cliente.objects.count(), 0)

    def test_excluir_protegido_redireciona_com_erro(self):
        c = Cliente.objects.create(estabelecimento=self.est, apelido="Com Atendimento")
        criar_atendimento(self.est, cliente=c)
        resp = self.client.post(reverse("cliente_excluir", args=[c.pk]))
        self.assertRedirects(resp, reverse("clientes"))
        self.assertTrue(Cliente.objects.filter(pk=c.pk).exists())
        msgs = [str(m) for m in resp.wsgi_request._messages]
        self.assertTrue(any("Não é possível excluir" in m for m in msgs))

    def test_anonimo_redireciona(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("clientes")), reverse("home"))


# ===========================================================================
# Ramos restantes de clientes
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ClienteRamosTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_criar_via_get_apenas_redireciona(self):
        resp = self.client.get(reverse("cliente_criar"))
        self.assertRedirects(resp, reverse("clientes"))

    def test_editar_sem_apelido_nao_altera(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        resp = self.client.post(
            reverse("cliente_editar", args=[cliente.pk]), {"apelido": " "}
        )
        self.assertEqual(resp.status_code, 200)
        cliente.refresh_from_db()
        self.assertEqual(cliente.apelido, "Ana")

    def test_excluir_via_get_nao_remove(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        resp = self.client.get(reverse("cliente_excluir", args=[cliente.pk]))
        self.assertRedirects(resp, reverse("clientes"))
        self.assertTrue(Cliente.objects.filter(pk=cliente.pk).exists())

    def test_lista_calcula_dias_desde_ultimo_atendimento(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        criar_atendimento(self.est, cliente=cliente, data=date.today())
        resp = self.client.get(reverse("clientes"))
        self.assertEqual(resp.status_code, 200)
        listado = resp.context["clientes"][0]
        self.assertEqual(listado.ultimo_label, "hoje")
        self.assertEqual(listado.dias_desde_ultimo, 0)
