"""CRUD de custos avulsos e validacoes de categoria."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core import views

from braid_system.core.models import (
    CategoriaCusto,
    Custo,
)

from .utils import (
    HASHERS_RAPIDOS,
    AutenticadoComEstabelecimentoMixin,
)


# ===========================================================================
# 15. CRUD de custos avulsos
# ===========================================================================
class CustoViewTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cat = CategoriaCusto.objects.create(
            nome="Aluguel", vinculado_atendimento=False
        )

    def test_listar(self):
        self.assertEqual(self.client.get(reverse("custos")).status_code, 200)

    def test_listar_mes_vazio_nao_quebra(self):
        # regressao: ?mes=&ano= nao deve gerar ValueError
        self.assertEqual(
            self.client.get(reverse("custos"), {"mes": "", "ano": ""}).status_code, 200
        )

    def test_criar(self):
        resp = self.client.post(
            reverse("custo_criar"),
            {
                "categoria_custo": str(self.cat.pk),
                "descricao": "Junho",
                "data": "2026-06-10",
                "valor": "800,00",
                "mes": "6",
                "ano": "2026",
            },
        )
        self.assertEqual(resp.status_code, 302)
        custo = Custo.objects.get()
        self.assertEqual(custo.valor, Decimal("800.00"))
        self.assertIsNone(custo.atendimento)

    def test_criar_categoria_vinculada_invalida(self):
        vinc = CategoriaCusto.objects.create(nome="Cabelo", vinculado_atendimento=True)
        resp = self.client.post(
            reverse("custo_criar"),
            {
                "categoria_custo": str(vinc.pk),
                "descricao": "X",
                "data": "2026-06-10",
                "valor": "50",
                "mes": "6",
                "ano": "2026",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_criar_campos_faltando(self):
        resp = self.client.post(reverse("custo_criar"), {"mes": "6", "ano": "2026"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_criar_sem_estabelecimento(self):
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        resp = self.client.post(
            reverse("custo_criar"),
            {"categoria_custo": str(self.cat.pk), "data": "2026-06-10", "valor": "50"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_editar(self):
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=self.cat,
            descricao="V",
            data=date(2026, 6, 1),
            valor=Decimal("100"),
        )
        resp = self.client.post(
            reverse("custo_editar", args=[custo.pk]),
            {
                "categoria_custo": str(self.cat.pk),
                "descricao": "Atualizado",
                "data": "2026-06-15",
                "valor": "250",
                "mes": "6",
                "ano": "2026",
            },
        )
        self.assertEqual(resp.status_code, 302)
        custo.refresh_from_db()
        self.assertEqual(custo.valor, Decimal("250"))
        self.assertEqual(custo.descricao, "Atualizado")

    def test_excluir(self):
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=self.cat,
            descricao="D",
            data=date(2026, 6, 1),
            valor=Decimal("10"),
        )
        resp = self.client.post(reverse("custo_excluir", args=[custo.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_anonimo_redireciona(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse("custos")), reverse("home"))


# ===========================================================================
# Ramos restantes de custos avulsos
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class CustoRamosTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def _criar_categorias(self):
        pai = CategoriaCusto.objects.create(nome="Estrutura")
        folha = CategoriaCusto.objects.create(nome="Aluguel", nivel_superior=pai)
        return pai, folha

    def test_criar_via_get_apenas_redireciona(self):
        resp = self.client.get(reverse("custo_criar"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/custos/", resp["Location"])

    def test_criar_categoria_com_subcategorias_rejeitada(self):
        pai, _folha = self._criar_categorias()
        resp = self.client.post(
            reverse("custo_criar"),
            {
                "categoria_custo": str(pai.pk),
                "descricao": "X",
                "data": "2026-06-01",
                "valor": "10",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_criar_erro_interno_exibe_erro(self):
        _pai, folha = self._criar_categorias()
        with mock.patch.object(
            views.Custo.objects, "create", side_effect=RuntimeError("boom")
        ):
            resp = self.client.post(
                reverse("custo_criar"),
                {
                    "categoria_custo": str(folha.pk),
                    "descricao": "X",
                    "data": "2026-06-01",
                    "valor": "10",
                },
            )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Custo.objects.count(), 0)

    def test_editar_categoria_com_subcategorias_rejeitada(self):
        pai, folha = self._criar_categorias()
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=folha,
            descricao="Aluguel",
            data=date(2026, 6, 1),
            valor=Decimal("100"),
        )
        resp = self.client.post(
            reverse("custo_editar", args=[custo.pk]),
            {
                "categoria_custo": str(pai.pk),
                "descricao": "Aluguel",
                "data": "2026-06-01",
                "valor": "100",
            },
        )
        self.assertEqual(resp.status_code, 302)
        custo.refresh_from_db()
        self.assertEqual(custo.categoria_custo, folha)

    def test_editar_categoria_inexistente_exibe_erro(self):
        _pai, folha = self._criar_categorias()
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=folha,
            descricao="Aluguel",
            data=date(2026, 6, 1),
            valor=Decimal("100"),
        )
        resp = self.client.post(
            reverse("custo_editar", args=[custo.pk]),
            {
                "categoria_custo": "",
                "descricao": "Aluguel",
                "data": "2026-06-01",
                "valor": "100",
            },
        )
        self.assertEqual(resp.status_code, 302)
        custo.refresh_from_db()
        self.assertEqual(custo.valor, Decimal("100"))

    def test_excluir_via_get_nao_remove(self):
        _pai, folha = self._criar_categorias()
        custo = Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=folha,
            descricao="Aluguel",
            data=date(2026, 6, 1),
            valor=Decimal("100"),
        )
        resp = self.client.get(reverse("custo_excluir", args=[custo.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Custo.objects.filter(pk=custo.pk).exists())
