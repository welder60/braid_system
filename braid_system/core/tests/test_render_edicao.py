"""GET dos formularios de edicao (render com 'editando' no contexto)."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from braid_system.core.models import (
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    CategoriaCusto,
    Cliente,
    Custo,
    EstabelecimentoUsuario,
    Pagamento,
)

from .utils import (
    AdminLogadoMixin,
    AutenticadoComEstabelecimentoMixin,
    criar_atendimento,
    criar_estabelecimento,
    criar_usuario,
)


class EditFormRenderTests(AdminLogadoMixin, TestCase):
    """GET nos formularios de edicao deve renderizar (ramo 'editando')."""

    def test_estabelecimento_editar_get(self):
        est = criar_estabelecimento()
        self.assertEqual(
            self.client.get(
                reverse("estabelecimento_editar", args=[est.pk])
            ).status_code,
            200,
        )

    def test_categoria_editar_get(self):
        cat = CategoriaCusto.objects.create(nome="C")
        self.assertEqual(
            self.client.get(
                reverse("categoria_custo_editar", args=[cat.pk])
            ).status_code,
            200,
        )

    def test_caracteristica_editar_get(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        self.assertEqual(
            self.client.get(
                reverse("caracteristica_atendimento_editar", args=[c.pk])
            ).status_code,
            200,
        )

    def test_opcao_editar_get(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        o = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=c, nome="Box"
        )
        self.assertEqual(
            self.client.get(
                reverse("opcao_caracteristica_editar", args=[c.pk, o.pk])
            ).status_code,
            200,
        )

    def test_usuario_editar_get(self):
        u = criar_usuario(email="ed@b.com")
        self.assertEqual(
            self.client.get(reverse("usuario_editar", args=[u.pk])).status_code, 200
        )

    def test_acesso_editar_get(self):
        est = criar_estabelecimento()
        u = criar_usuario(email="al@b.com")
        v = EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=u)
        self.assertEqual(
            self.client.get(reverse("acesso_editar", args=[v.pk])).status_code, 200
        )

    def test_admin_painel_get(self):
        self.assertEqual(self.client.get(reverse("admin_painel")).status_code, 200)


class EditFormRenderTenantTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_relatorios_get(self):
        self.assertEqual(self.client.get(reverse("relatorios")).status_code, 200)

    def test_cliente_editar_get(self):
        c = Cliente.objects.create(estabelecimento=self.est, apelido="Rita")
        self.assertEqual(
            self.client.get(reverse("cliente_editar", args=[c.pk])).status_code, 200
        )

    def test_atendimento_editar_get_calcula_totais(self):
        at = criar_atendimento(self.est, duracao=125)
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=None, valor=Decimal("150")
        )
        resp = self.client.get(reverse("atendimento_editar", args=[at.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["editando"].duracao_edit, "02:05")

    def test_custo_editar_get(self):
        cat = CategoriaCusto.objects.create(nome="Aluguel", vinculado_atendimento=False)
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            descricao="X",
            data=date(2026, 6, 1),
            valor=Decimal("100"),
        )
        self.assertEqual(
            self.client.get(reverse("custo_editar", args=[custo.pk])).status_code, 200
        )
