"""Isolamento de dados entre estabelecimentos (seguranca multi-tenant)."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from braid_system.core.models import (
    CategoriaCusto,
    Cliente,
    Custo,
    EstabelecimentoUsuario,
)

from .utils import (
    criar_estabelecimento,
    criar_usuario,
)


class IsolamentoDadosTests(TestCase):
    """Dados operacionais visiveis apenas a vinculados (admin a parte)."""

    def setUp(self):
        self.user = criar_usuario(email="pro@b.com", tipo="profissional")
        self.est_ok = criar_estabelecimento("Vinculado")
        self.est_alheio = criar_estabelecimento("Alheio")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=self.est_ok, usuario=self.user
        )
        self.client.force_login(self.user)
        self._ativar(self.est_ok)

    def _ativar(self, est):
        s = self.client.session
        s["estabelecimento_ativo_id"] = str(est.pk)
        s.save()

    def test_sessao_para_estabelecimento_nao_vinculado_e_ignorada(self):
        Cliente.objects.create(estabelecimento=self.est_alheio, apelido="Secreto")
        self._ativar(self.est_alheio)  # tenta forcar um estabelecimento alheio
        resp = self.client.get(reverse("clientes"))
        self.assertEqual(list(resp.context["clientes"]), [])

    def test_acesso_revogado_esconde_dados(self):
        Cliente.objects.create(estabelecimento=self.est_ok, apelido="Antigo")
        EstabelecimentoUsuario.objects.filter(
            usuario=self.user, estabelecimento=self.est_ok
        ).delete()
        resp = self.client.get(reverse("clientes"))
        self.assertEqual(list(resp.context["clientes"]), [])

    def test_idor_cliente_de_outro_estabelecimento_404(self):
        c = Cliente.objects.create(estabelecimento=self.est_alheio, apelido="De Alheio")
        self.assertEqual(
            self.client.post(
                reverse("cliente_editar", args=[c.pk]), {"apelido": "x"}
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("cliente_excluir", args=[c.pk])).status_code, 404
        )
        self.assertTrue(Cliente.objects.filter(pk=c.pk).exists())

    def test_idor_custo_de_outro_estabelecimento_404(self):
        cat = CategoriaCusto.objects.create(nome="Aluguel", vinculado_atendimento=False)
        custo = Custo.objects.create(
            estabelecimento=self.est_alheio,
            categoria_custo=cat,
            descricao="X",
            data=date(2026, 6, 1),
            valor=Decimal("10"),
        )
        self.assertEqual(
            self.client.post(reverse("custo_editar", args=[custo.pk]), {}).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("custo_excluir", args=[custo.pk])).status_code, 404
        )
        self.assertTrue(Custo.objects.filter(pk=custo.pk).exists())

    def test_admin_ve_qualquer_estabelecimento(self):
        Cliente.objects.create(
            estabelecimento=self.est_alheio, apelido="Visivel ao admin"
        )
        self.client.force_login(criar_usuario(email="adm2@b.com", tipo="admin"))
        self._ativar(self.est_alheio)
        resp = self.client.get(reverse("clientes"))
        apelidos = {c.apelido for c in resp.context["clientes"]}
        self.assertIn("Visivel ao admin", apelidos)
