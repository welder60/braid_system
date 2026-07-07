"""Funcoes utilitarias puras de views.py (parse/formatacao)."""

from datetime import time
from decimal import Decimal

from django.test import SimpleTestCase

from braid_system.core import views


# ===========================================================================
# 1. Funcoes utilitarias (puras) — nao precisam de banco
# ===========================================================================
class HelperFunctionTests(SimpleTestCase):
    def test_fmt_duracao_vazio(self):
        self.assertEqual(views._fmt_duracao(0), "")
        self.assertEqual(views._fmt_duracao(None), "")

    def test_fmt_duracao_somente_minutos(self):
        self.assertEqual(views._fmt_duracao(45), "45min")
        self.assertEqual(views._fmt_duracao(5), "5min")

    def test_fmt_duracao_horas_exatas(self):
        self.assertEqual(views._fmt_duracao(60), "1h")
        self.assertEqual(views._fmt_duracao(600), "10h")

    def test_fmt_duracao_horas_e_minutos(self):
        self.assertEqual(views._fmt_duracao(90), "1h30")
        self.assertEqual(views._fmt_duracao(125), "2h05")

    def test_parse_hora_valida(self):
        self.assertEqual(views._parse_hora("14:30"), time(14, 30))
        self.assertEqual(views._parse_hora("14:30:45"), time(14, 30, 45))
        self.assertEqual(views._parse_hora("  09:05  "), time(9, 5))

    def test_parse_hora_invalida(self):
        self.assertIsNone(views._parse_hora(""))
        self.assertIsNone(views._parse_hora(None))
        self.assertIsNone(views._parse_hora("abc"))
        self.assertIsNone(views._parse_hora("25:99"))

    def test_duracao_para_minutos(self):
        self.assertEqual(views._duracao_para_minutos("01:30"), 90)
        self.assertEqual(views._duracao_para_minutos("2"), 120)
        self.assertEqual(views._duracao_para_minutos("1:30:00"), 90)

    def test_duracao_para_minutos_invalida_ou_zero(self):
        self.assertIsNone(views._duracao_para_minutos(""))
        self.assertIsNone(views._duracao_para_minutos(None))
        self.assertIsNone(views._duracao_para_minutos("0:00"))
        self.assertIsNone(views._duracao_para_minutos("abc"))

    def test_parse_dinheiro_formatos(self):
        self.assertEqual(views._parse_dinheiro("120.50"), Decimal("120.50"))
        self.assertEqual(views._parse_dinheiro("120,50"), Decimal("120.50"))
        self.assertEqual(views._parse_dinheiro("1.234,56"), Decimal("1234.56"))
        self.assertEqual(views._parse_dinheiro("100"), Decimal("100"))

    def test_parse_dinheiro_invalido(self):
        self.assertIsNone(views._parse_dinheiro(""))
        self.assertIsNone(views._parse_dinheiro(None))
        self.assertIsNone(views._parse_dinheiro("abc"))


# ===========================================================================
# Helpers de formatacao (funcoes puras)
# ===========================================================================
class HelperFormatTests(SimpleTestCase):
    def test_fmt_money_br(self):
        self.assertEqual(views._fmt_money_br(Decimal("0")), "0,00")
        self.assertEqual(views._fmt_money_br(Decimal("150")), "150,00")
        self.assertEqual(views._fmt_money_br(Decimal("1234.5")), "1.234,50")
        self.assertEqual(views._fmt_money_br(Decimal("1234567.89")), "1.234.567,89")
        self.assertEqual(views._fmt_money_br(None), "0,00")

    def test_fmt_money_br_negativo(self):
        self.assertEqual(views._fmt_money_br(Decimal("-50")), "-50,00")
        self.assertEqual(views._fmt_money_br(Decimal("-1234.56")), "-1.234,56")

    def test_fmt_horas_br(self):
        self.assertEqual(views._fmt_horas_br(0), "0h")
        self.assertEqual(views._fmt_horas_br(None), "0h")
        self.assertEqual(views._fmt_horas_br(45), "45min")
        self.assertEqual(views._fmt_horas_br(120), "2h")
        self.assertEqual(views._fmt_horas_br(150), "2h30")

    def test_dias_label(self):
        self.assertEqual(views._dias_label(0), "hoje")
        self.assertEqual(views._dias_label(1), "ontem")
        self.assertEqual(views._dias_label(3), "há 3 dias")
        self.assertEqual(views._dias_label(7), "há 1 semana")
        self.assertEqual(views._dias_label(15), "há 2 semanas")
        self.assertEqual(views._dias_label(31), "há 1 mes")
        self.assertEqual(views._dias_label(65), "há 2 meses")
        self.assertEqual(views._dias_label(365), "há 1 ano")
        self.assertEqual(views._dias_label(800), "há 2 anos")
