"""Relatorios da gestao com movimento real."""

from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import (
    CategoriaCusto,
    Custo,
    Pagamento,
)

from .utils import (
    HASHERS_RAPIDOS,
    AutenticadoComEstabelecimentoMixin,
    criar_atendimento,
)


# ===========================================================================
# Relatorios (gestao) com movimento real
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class RelatoriosComDadosTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_relatorio_calcula_faturamento_custos_e_lucro(self):
        at = criar_atendimento(self.est, data=date(2026, 1, 15), duracao=120)
        Pagamento.objects.create(atendimento=at, valor=Decimal("200"))
        cat = CategoriaCusto.objects.create(nome="Insumos")
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            descricao="Tinta",
            data=date(2026, 1, 10),
            valor=Decimal("50"),
        )
        resp = self.client.get(reverse("relatorios"))
        self.assertEqual(resp.status_code, 200)
        jan = next(
            m
            for m in resp.context["relatorios_meses"]
            if m["ano"] == 2026 and m["mes"] == 1
        )
        self.assertEqual(jan["total_atendimentos"], 1)
        self.assertEqual(jan["total_faturado"], "200,00")
        self.assertEqual(jan["total_custos"], "50,00")
        self.assertEqual(jan["lucro_total"], "150,00")
        self.assertTrue(jan["lucro_positivo"])
        self.assertEqual(jan["lucro_por_atendimento"], "150,00")
        self.assertEqual(jan["lucro_por_hora"], "75,00")
        self.assertEqual(jan["duracao_media"], "2h")

    def test_relatorio_mes_com_prejuizo(self):
        at = criar_atendimento(self.est, data=date(2026, 2, 10))
        Pagamento.objects.create(atendimento=at, valor=Decimal("100"))
        cat = CategoriaCusto.objects.create(nome="Insumos")
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            descricao="Tinta",
            data=date(2026, 2, 5),
            valor=Decimal("150"),
        )
        resp = self.client.get(reverse("relatorios"))
        fev = next(
            m
            for m in resp.context["relatorios_meses"]
            if m["ano"] == 2026 and m["mes"] == 2
        )
        self.assertEqual(fev["lucro_total"], "-50,00")
        self.assertFalse(fev["lucro_positivo"])
