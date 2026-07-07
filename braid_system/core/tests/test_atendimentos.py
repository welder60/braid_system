"""Fluxo de atendimentos: CRUD, validacoes e verificacao de duplicidade."""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core import views
from braid_system.core.models import (
    Atendimento,
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    CategoriaCusto,
    Cliente,
    Custo,
    FormaPagamento,
    Pagamento,
)

from .utils import (
    HASHERS_RAPIDOS,
    AutenticadoComEstabelecimentoMixin,
    criar_atendimento,
    criar_estabelecimento,
)


# ===========================================================================
# 14. Fluxo de atendimento (regressao do bug forma_pagamento)
# ===========================================================================
class AtendimentoViewTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("atendimentos")).status_code, 200)

    def test_get_criar_redireciona(self):
        # GET (nao-POST) em atendimento_criar volta para a listagem
        self.assertRedirects(
            self.client.get(reverse("atendimento_criar")), reverse("atendimentos")
        )

    def test_criar_com_novo_cliente_e_pagamento(self):
        """Regressao: antes quebrava por forma_pagamento='' numa FK."""
        resp = self.client.post(
            reverse("atendimento_criar"),
            {
                "novo_cliente": "Maria",
                "data": "2026-06-01",
                "hora": "14:30",
                "duracao": "02:00",
                "pagamento_valor": "150,00",
            },
        )
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertEqual(Atendimento.objects.count(), 1)
        at = Atendimento.objects.get()
        self.assertEqual(at.cliente.apelido, "Maria")
        self.assertEqual(at.duracao, 120)
        pag = at.pagamentos.get()
        self.assertEqual(pag.valor, Decimal("150.00"))
        self.assertIsNone(pag.forma_pagamento)

    def test_criar_com_caracteristicas_e_custos(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Joana")
        carac = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Q"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=carac, nome="Box"
        )
        cat = CategoriaCusto.objects.create(nome="Cabelo", vinculado_atendimento=True)
        resp = self.client.post(
            reverse("atendimento_criar"),
            {
                "cliente_id": str(cliente.pk),
                "data": "2026-06-02",
                "hora": "09:00",
                "pagamento_valor": "200",
                "opcoes": [str(opcao.pk)],
                f"custo_{cat.pk}": "35,50",
            },
        )
        self.assertRedirects(resp, reverse("atendimentos"))
        at = Atendimento.objects.get()
        self.assertEqual(at.caracteristicas.count(), 1)
        custo = at.custos.get()
        self.assertEqual(custo.valor, Decimal("35.50"))
        self.assertEqual(custo.categoria_custo, cat)

    def test_criar_sem_cliente_falha(self):
        resp = self.client.post(
            reverse("atendimento_criar"),
            {"data": "2026-06-01", "hora": "14:30", "pagamento_valor": "150"},
        )
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_criar_pagamento_invalido_falha(self):
        resp = self.client.post(
            reverse("atendimento_criar"),
            {
                "novo_cliente": "Maria",
                "data": "2026-06-01",
                "hora": "14:30",
                "pagamento_valor": "abc",
            },
        )
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_criar_sem_estabelecimento_ativo(self):
        sessao = self.client.session
        del sessao["estabelecimento_ativo_id"]
        sessao.save()
        resp = self.client.post(
            reverse("atendimento_criar"),
            {
                "novo_cliente": "Maria",
                "data": "2026-06-01",
                "hora": "14:30",
                "pagamento_valor": "150",
            },
        )
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_editar_atualiza_pagamento(self):
        at = criar_atendimento(self.est)
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=None, valor=Decimal("100")
        )
        resp = self.client.post(
            reverse("atendimento_editar", args=[at.pk]),
            {
                "cliente_id": str(at.cliente_id),
                "data": "2026-07-01",
                "hora": "10:00",
                "duracao": "01:15",
                "pagamento_valor": "180",
            },
        )
        self.assertRedirects(resp, reverse("atendimentos") + "?mes=6&ano=2026")
        at.refresh_from_db()
        self.assertEqual(at.data, date(2026, 7, 1))
        self.assertEqual(at.duracao, 75)
        self.assertEqual(at.pagamentos.get().valor, Decimal("180"))

    def test_editar_outro_estabelecimento_404(self):
        outro = criar_estabelecimento("Outro")
        at = criar_atendimento(outro)
        resp = self.client.post(
            reverse("atendimento_editar", args=[at.pk]),
            {"data": "2026-07-01", "hora": "10:00", "pagamento_valor": "180"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_excluir(self):
        at = criar_atendimento(self.est)
        resp = self.client.post(reverse("atendimento_excluir", args=[at.pk]))
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertEqual(Atendimento.objects.count(), 0)


# ===========================================================================
# Endpoint AJAX de verificacao de duplicidade de atendimento
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class AtendimentoVerificarTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def test_anonimo_403(self):
        self.client.logout()
        resp = self.client.get(reverse("atendimento_verificar"))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json(), {"error": "auth"})

    def test_parametros_ausentes_sem_duplicata(self):
        resp = self.client.get(reverse("atendimento_verificar"))
        self.assertEqual(resp.json(), {"duplicata": False})

    def test_data_invalida_sem_duplicata(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        resp = self.client.get(
            reverse("atendimento_verificar"),
            {"cliente_id": str(cliente.pk), "data": "06/01/2026"},
        )
        self.assertEqual(resp.json(), {"duplicata": False})

    def test_detecta_duplicata(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        criar_atendimento(self.est, cliente=cliente, data=date(2026, 6, 1))
        resp = self.client.get(
            reverse("atendimento_verificar"),
            {"cliente_id": str(cliente.pk), "data": "2026-06-01"},
        )
        self.assertEqual(resp.json(), {"duplicata": True})

    def test_excluir_pk_ignora_o_proprio_atendimento(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        at = criar_atendimento(self.est, cliente=cliente, data=date(2026, 6, 1))
        resp = self.client.get(
            reverse("atendimento_verificar"),
            {
                "cliente_id": str(cliente.pk),
                "data": "2026-06-01",
                "excluir_pk": str(at.pk),
            },
        )
        self.assertEqual(resp.json(), {"duplicata": False})


# ===========================================================================
# Ramos de validacao de atendimento_criar / editar / excluir
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class AtendimentoRamosTests(AutenticadoComEstabelecimentoMixin, TestCase):
    def _post_criar(self, **extra):
        dados = {
            "novo_cliente": "Ana",
            "data": "2026-06-01",
            "hora": "14:00",
            "pagamento_valor": "100,00",
        }
        dados.update(extra)
        return self.client.post(reverse("atendimento_criar"), dados)

    def test_criar_sem_data(self):
        resp = self._post_criar(data="")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_criar_data_invalida(self):
        resp = self._post_criar(data="31-31-2026")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_criar_data_futura(self):
        futura = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        resp = self._post_criar(data=futura)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Atendimento.objects.count(), 0)

    def test_criar_duplicado_no_mesmo_dia(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        criar_atendimento(self.est, cliente=cliente, data=date(2026, 6, 1))
        resp = self._post_criar(novo_cliente="", cliente_id=str(cliente.pk))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Atendimento.objects.count(), 1)

    def test_criar_com_forma_pagamento_e_custo_invalido(self):
        forma = FormaPagamento.objects.create(nome="Pix")
        cat_vinc = CategoriaCusto.objects.create(
            nome="Cabelo", vinculado_atendimento=True
        )
        cat_livre = CategoriaCusto.objects.create(nome="Aluguel")
        resp = self._post_criar(
            forma_pagamento_id=str(forma.pk),
            **{
                f"custo_{cat_vinc.pk}": "0",  # <= 0: ignorado
                f"custo_{cat_livre.pk}": "25,00",  # nao vinculada: ignorada
            },
        )
        self.assertEqual(resp.status_code, 302)
        at = Atendimento.objects.get()
        self.assertEqual(at.pagamentos.first().forma_pagamento, forma)
        self.assertEqual(at.custos.count(), 0)

    def test_criar_erro_interno_exibe_mensagem(self):
        with mock.patch.object(
            views.Pagamento.objects, "create", side_effect=RuntimeError("boom")
        ):
            resp = self._post_criar()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Atendimento.objects.count(), 0)

    def _post_editar(self, at, **extra):
        dados = {
            "cliente_id": str(at.cliente_id),
            "data": "2026-06-02",
            "hora": "15:00",
            "pagamento_valor": "80,00",
        }
        dados.update(extra)
        return self.client.post(reverse("atendimento_editar", args=[at.pk]), dados)

    def test_editar_data_invalida(self):
        at = criar_atendimento(self.est)
        resp = self._post_editar(at, data="xx-xx")
        self.assertEqual(resp.status_code, 200)
        at.refresh_from_db()
        self.assertEqual(at.data, date(2026, 6, 1))

    def test_editar_data_futura(self):
        at = criar_atendimento(self.est)
        futura = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        resp = self._post_editar(at, data=futura)
        self.assertEqual(resp.status_code, 200)
        at.refresh_from_db()
        self.assertEqual(at.data, date(2026, 6, 1))

    def test_editar_para_data_ja_atendida_do_cliente(self):
        cliente = Cliente.objects.create(estabelecimento=self.est, apelido="Ana")
        criar_atendimento(self.est, cliente=cliente, data=date(2026, 6, 2))
        at = criar_atendimento(self.est, cliente=cliente, data=date(2026, 6, 3))
        resp = self._post_editar(at, data="2026-06-02")
        self.assertEqual(resp.status_code, 200)
        at.refresh_from_db()
        self.assertEqual(at.data, date(2026, 6, 3))

    def test_editar_com_novo_cliente(self):
        at = criar_atendimento(self.est)
        resp = self._post_editar(at, cliente_id="", novo_cliente="Bia")
        self.assertEqual(resp.status_code, 302)
        at.refresh_from_db()
        self.assertEqual(at.cliente.apelido, "Bia")

    def test_editar_cria_pagamento_quando_nao_existe(self):
        at = criar_atendimento(self.est)
        self.assertEqual(at.pagamentos.count(), 0)
        resp = self._post_editar(at)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(at.pagamentos.count(), 1)
        self.assertEqual(at.pagamentos.first().valor, Decimal("80.00"))

    def test_editar_sincroniza_custos_vinculados(self):
        cat = CategoriaCusto.objects.create(nome="Cabelo", vinculado_atendimento=True)
        cat2 = CategoriaCusto.objects.create(nome="Tinta", vinculado_atendimento=True)
        at = criar_atendimento(self.est)
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            atendimento=at,
            descricao=cat.nome,
            data=at.data,
            valor=Decimal("30"),
        )
        resp = self._post_editar(
            at,
            **{
                f"custo_{cat.pk}": "0",  # zera: remove o custo existente
                f"custo_{cat2.pk}": "12,50",  # novo: cria
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(at.custos.count(), 1)
        custo = at.custos.get()
        self.assertEqual(custo.categoria_custo, cat2)
        self.assertEqual(custo.valor, Decimal("12.50"))

    def test_editar_erro_interno_exibe_mensagem(self):
        at = criar_atendimento(self.est)
        with mock.patch.object(
            views.Pagamento.objects, "create", side_effect=RuntimeError("boom")
        ):
            resp = self._post_editar(at)
        self.assertEqual(resp.status_code, 200)

    def test_editar_sem_cliente_e_sem_hora(self):
        at = criar_atendimento(self.est)
        resp = self._post_editar(
            at, cliente_id="", novo_cliente="", hora="", pagamento_valor=""
        )
        self.assertEqual(resp.status_code, 200)
        at.refresh_from_db()
        self.assertEqual(at.hora.strftime("%H:%M"), "14:30")

    def test_editar_com_forma_pagamento_e_opcoes(self):
        forma = FormaPagamento.objects.create(nome="Cartao Loja")
        car = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=car, nome="Box"
        )
        at = criar_atendimento(self.est)
        Pagamento.objects.create(atendimento=at, valor=Decimal("10"))
        resp = self._post_editar(
            at, forma_pagamento_id=str(forma.pk), opcoes=[str(opcao.pk)]
        )
        self.assertEqual(resp.status_code, 302)
        pagamento = at.pagamentos.get()
        self.assertEqual(pagamento.forma_pagamento, forma)
        self.assertEqual(pagamento.valor, Decimal("80.00"))
        self.assertEqual(at.caracteristicas.get().opcao, opcao)

    def test_editar_atualiza_custo_existente_da_categoria(self):
        cat = CategoriaCusto.objects.create(nome="Cabelo", vinculado_atendimento=True)
        at = criar_atendimento(self.est)
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            atendimento=at,
            descricao=cat.nome,
            data=at.data,
            valor=Decimal("30"),
        )
        resp = self._post_editar(at, **{f"custo_{cat.pk}": "45,00"})
        self.assertEqual(resp.status_code, 302)
        custo = at.custos.get()
        self.assertEqual(custo.valor, Decimal("45.00"))

    def test_editar_ignora_custo_de_categoria_inexistente(self):
        import uuid

        at = criar_atendimento(self.est)
        resp = self._post_editar(at, **{f"custo_{uuid.uuid4()}": "45,00"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(at.custos.count(), 0)

    def test_excluir_via_get_nao_remove(self):
        at = criar_atendimento(self.est)
        resp = self.client.get(reverse("atendimento_excluir", args=[at.pk]))
        self.assertRedirects(resp, reverse("atendimentos"))
        self.assertTrue(Atendimento.objects.filter(pk=at.pk).exists())

    def test_editar_get_expoe_estado_do_wizard(self):
        cat = CategoriaCusto.objects.create(nome="Cabelo", vinculado_atendimento=True)
        forma = FormaPagamento.objects.create(nome="Pix")
        at = criar_atendimento(self.est)
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=forma, valor=Decimal("90")
        )
        Custo.objects.create(
            estabelecimento=self.est,
            categoria_custo=cat,
            atendimento=at,
            descricao=cat.nome,
            data=at.data,
            valor=Decimal("15"),
        )
        resp = self.client.get(reverse("atendimento_editar", args=[at.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(str(cat.pk), resp.context["edicao_json"])
