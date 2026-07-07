"""
Testes do painel do consultor (dashboards, relatorios e exportacoes CSV).

Organizacao:
    - ConsultorAcessoTests ................ restricao de acesso (@_consultor_required)
    - ConsultorContextTests ............... helpers de contexto/estabelecimentos
    - ConsultorPainelTests ................ dashboard com KPIs e grafico
    - ConsultorRelatoriosTests ............ relatorio mensal por ano
    - ConsultorExportarCsvTests ........... CSV do resumo financeiro
    - ConsultorRelatorioAtendimentosTests . relatorio detalhado por periodo
    - ConsultorExportarCsvAtendimentosTests CSV detalhado de atendimentos

Rodar com:  python manage.py test braid_system.core
"""

import json
from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import (
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    AtendimentoCaracteristica,
    CategoriaCusto,
    Cliente,
    Custo,
    EstabelecimentoUsuario,
    FormaPagamento,
    Pagamento,
)
from .utils import (
    HASHERS_RAPIDOS,
    criar_atendimento,
    criar_estabelecimento,
    criar_usuario,
)
from braid_system.core.views import _get_estabelecimentos_consultor


ROTAS_CONSULTOR = [
    "consultor_painel",
    "consultor_relatorios",
    "consultor_exportar_csv",
    "consultor_relatorio_atendimentos",
    "consultor_exportar_csv_atendimentos",
]


class ConsultorLogadoMixin:
    """Consultor autenticado, vinculado a um estabelecimento ativo na sessao."""

    def setUp(self):
        super().setUp()
        self.consultor = criar_usuario(
            email="consultor@b.com", nome="Consultora", tipo="consultor"
        )
        self.est = criar_estabelecimento("Salao Consultoria")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=self.est, usuario=self.consultor, tipo_acesso="visualizar"
        )
        self.client.force_login(self.consultor)
        sessao = self.client.session
        sessao["estabelecimento_ativo_id"] = str(self.est.pk)
        sessao.save()

    def criar_movimento_jan_2026(self):
        """Um atendimento pago (R$200, 2h) e um custo avulso (R$50) em jan/2026."""
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        at = criar_atendimento(
            self.est, cliente=cliente, data=date(2026, 1, 15), duracao=120
        )
        forma = FormaPagamento.objects.create(nome="Pix")
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=forma, valor=Decimal("200")
        )
        cat = CategoriaCusto.objects.create(nome="Insumos")
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            descricao="Tinta",
            data=date(2026, 1, 10),
            valor=Decimal("50"),
        )
        return at


# ===========================================================================
# Restricao de acesso ao painel
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorAcessoTests(TestCase):
    def test_anonimo_redireciona_para_home(self):
        for nome in ROTAS_CONSULTOR:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("home"))

    def test_profissional_redireciona_para_gestao(self):
        user = criar_usuario()
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        self.client.force_login(user)
        for nome in ROTAS_CONSULTOR:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("gestao"))

    def test_admin_acessa(self):
        self.client.force_login(criar_usuario(email="a@b.com", tipo="admin"))
        resp = self.client.get(reverse("consultor_painel"))
        self.assertEqual(resp.status_code, 200)


# ===========================================================================
# Contexto compartilhado do painel
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorContextTests(TestCase):
    def test_get_estabelecimentos_consultor_admin_ve_todos(self):
        admin = criar_usuario(email="a@b.com", tipo="admin")
        criar_estabelecimento("Alfa")
        criar_estabelecimento("Beta")
        nomes = [e.nome for e in _get_estabelecimentos_consultor(admin)]
        self.assertEqual(nomes, ["Alfa", "Beta"])

    def test_get_estabelecimentos_consultor_ve_somente_vinculados(self):
        consultor = criar_usuario(email="c@b.com", tipo="consultor")
        est = criar_estabelecimento("Alfa")
        criar_estabelecimento("Beta")
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=consultor)
        nomes = [e.nome for e in _get_estabelecimentos_consultor(consultor)]
        self.assertEqual(nomes, ["Alfa"])

    def test_fallback_seleciona_estabelecimento_unico(self):
        # Admin com um unico estabelecimento cadastrado: auto-selecao no painel.
        admin = criar_usuario(email="a@b.com", tipo="admin")
        est = criar_estabelecimento("Unico")
        self.client.force_login(admin)
        resp = self.client.get(reverse("consultor_painel"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["estabelecimento_ativo"], est)
        self.assertEqual(self.client.session["estabelecimento_ativo_id"], str(est.pk))


# ===========================================================================
# Dashboard principal
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorPainelTests(ConsultorLogadoMixin, TestCase):
    def test_painel_sem_estabelecimento_ativo(self):
        # Dois vinculos e nenhuma selecao na sessao: sem auto-selecao possivel.
        outro = criar_estabelecimento("Outro")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=outro, usuario=self.consultor, tipo_acesso="visualizar"
        )
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        resp = self.client.get(reverse("consultor_painel"))
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["estabelecimento_ativo"])

    def test_painel_com_movimento(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(reverse("consultor_painel"))
        self.assertEqual(resp.status_code, 200)

        jan = next(
            m
            for m in resp.context["relatorios_meses"]
            if m["ano"] == 2026 and m["mes"] == 1
        )
        self.assertEqual(jan["total_atendimentos"], 1)
        self.assertEqual(jan["total_faturado"], "200,00")
        self.assertEqual(jan["lucro_total"], "150,00")

        chart = json.loads(resp.context["chart_data_json"])
        self.assertIn("2026", chart)
        self.assertEqual(chart["2026"]["faturamento"][0], 200.0)
        self.assertEqual(chart["2026"]["custo"][0], 50.0)
        self.assertEqual(chart["2026"]["lucro"][0], 150.0)
        self.assertEqual(chart["2026"]["atendimentos"][0], 1)

        self.assertIn("kpi", resp.context)
        self.assertIn(2026, resp.context["chart_anos"])


# ===========================================================================
# Relatorio mensal por ano
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorRelatoriosTests(ConsultorLogadoMixin, TestCase):
    def test_relatorio_do_ano_com_totais(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(reverse("consultor_relatorios"), {"ano": "2026"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ano_selecionado"], 2026)

        meses = resp.context["relatorios_meses"]
        self.assertEqual(len(meses), 1)  # somente jan/2026 tem movimento
        self.assertEqual(meses[0]["mes"], 1)
        self.assertEqual(meses[0]["total_faturado"], "200,00")
        self.assertEqual(meses[0]["total_horas"], "2h")

        totais = resp.context["totais"]
        self.assertEqual(totais["atendimentos"], 1)
        self.assertEqual(totais["faturado"], "200,00")
        self.assertEqual(totais["custos"], "50,00")
        self.assertEqual(totais["lucro"], "150,00")
        self.assertTrue(totais["lucro_positivo"])

    def test_ano_invalido_cai_para_ano_corrente(self):
        resp = self.client.get(reverse("consultor_relatorios"), {"ano": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ano_selecionado"], date.today().year)

    def test_ano_fora_da_lista_cai_para_ano_corrente(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(reverse("consultor_relatorios"), {"ano": "1999"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["ano_selecionado"], date.today().year)


# ===========================================================================
# CSV do resumo financeiro
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorExportarCsvTests(ConsultorLogadoMixin, TestCase):
    def test_sem_estabelecimento_redireciona(self):
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        EstabelecimentoUsuario.objects.filter(usuario=self.consultor).delete()
        resp = self.client.get(reverse("consultor_exportar_csv"))
        self.assertEqual(resp.status_code, 302)

    def test_exporta_resumo_do_periodo(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(
            reverse("consultor_exportar_csv"), {"ano": "2026", "mes": "1"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("_2026_01", resp["Content-Disposition"])

        corpo = resp.content.decode("utf-8-sig")
        # Valores crus com virgula decimal; lucro/atendimento quantizado.
        self.assertIn("Jan/26;1;2h;200;50;150;150,00", corpo)

    def test_parametros_invalidos_exportam_tudo(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(reverse("consultor_exportar_csv"), {"ano": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Jan/26", resp.content.decode("utf-8-sig"))


# ===========================================================================
# Relatorio detalhado de atendimentos
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorRelatorioAtendimentosTests(ConsultorLogadoMixin, TestCase):
    def _movimento_com_caracteristica(self):
        at = self.criar_movimento_jan_2026()
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo de Tranca", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box Braids"
        )
        AtendimentoCaracteristica.objects.create(atendimento=at, opcao=opcao)
        return at

    def test_lista_atendimentos_do_periodo(self):
        self._movimento_com_caracteristica()
        resp = self.client.get(
            reverse("consultor_relatorio_atendimentos"),
            {"ano_ini": "2026", "mes_ini": "1", "ano_fim": "2026", "mes_fim": "1"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_atendimentos"], 1)
        self.assertEqual(resp.context["total_faturado"], "200,00")

        linha = resp.context["atendimentos"][0]
        self.assertEqual(linha["cliente"], "Ana")
        self.assertEqual(linha["valor"], "200,00")
        self.assertEqual(linha["formas_pagamento"], "Pix")
        self.assertEqual(linha["caracteristicas_vals"], ["Box Braids"])

    def test_periodo_invertido_e_corrigido(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(
            reverse("consultor_relatorio_atendimentos"),
            {"ano_ini": "2026", "mes_ini": "3", "ano_fim": "2026", "mes_fim": "1"},
        )
        self.assertEqual(resp.status_code, 200)
        # O periodo e normalizado: inicio passa a ser o menor dos dois.
        self.assertLessEqual(resp.context["data_ini"], resp.context["data_fim"])
        self.assertEqual(resp.context["mes_ini"], 1)
        self.assertEqual(resp.context["mes_fim"], 3)

    def test_parametros_invalidos_usam_padrao(self):
        resp = self.client.get(
            reverse("consultor_relatorio_atendimentos"), {"mes_ini": "abc"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["mes_ini"], 1)


# ===========================================================================
# CSV detalhado de atendimentos
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ConsultorExportarCsvAtendimentosTests(ConsultorLogadoMixin, TestCase):
    def test_sem_estabelecimento_redireciona(self):
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        EstabelecimentoUsuario.objects.filter(usuario=self.consultor).delete()
        resp = self.client.get(reverse("consultor_exportar_csv_atendimentos"))
        self.assertEqual(resp.status_code, 302)

    def test_exporta_detalhe_dos_atendimentos(self):
        at = self.criar_movimento_jan_2026()
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box Braids"
        )
        AtendimentoCaracteristica.objects.create(atendimento=at, opcao=opcao)

        resp = self.client.get(
            reverse("consultor_exportar_csv_atendimentos"),
            {"ano_ini": "2026", "mes_ini": "1", "ano_fim": "2026", "mes_fim": "1"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("_202601_202601", resp["Content-Disposition"])

        corpo = resp.content.decode("utf-8-sig")
        self.assertIn("Cliente", corpo)  # cabecalho
        self.assertIn("Tipo", corpo)  # coluna da caracteristica
        self.assertIn("15/01/2026", corpo)
        self.assertIn("Ana", corpo)
        self.assertIn("200,00", corpo)
        self.assertIn("Pix", corpo)
        self.assertIn("Box Braids", corpo)

    def test_parametros_invalidos_usam_padrao(self):
        self.criar_movimento_jan_2026()
        resp = self.client.get(
            reverse("consultor_exportar_csv_atendimentos"), {"ano_ini": "abc"}
        )
        self.assertEqual(resp.status_code, 200)
