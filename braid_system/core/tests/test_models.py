"""Modelos: autenticacao, dominio, regras on_delete e ramos de validacao."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase, override_settings

from braid_system.core.models import (
    AtendimentoCaracteristica,
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    CategoriaCusto,
    Cliente,
    Custo,
    EstabelecimentoUsuario,
    FormaPagamento,
    Pagamento,
)

from .utils import (
    HASHERS_RAPIDOS,
    Usuario,
    criar_atendimento,
    criar_estabelecimento,
    criar_usuario,
)


# ===========================================================================
# 2. Modelo Usuario + UsuarioManager (app security)
# ===========================================================================
class UsuarioModelTests(TestCase):
    def test_create_user_basico(self):
        u = Usuario.objects.create_user(
            email="a@b.com", nome="Ana", password="x123456789"
        )
        self.assertTrue(u.check_password("x123456789"))
        self.assertTrue(u.is_active)
        self.assertFalse(u.is_staff)
        self.assertFalse(u.is_superuser)

    def test_create_user_sem_email_levanta_erro(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(
                email="", nome="SemEmail", password="x123456789"
            )

    def test_create_user_normaliza_dominio_email(self):
        u = Usuario.objects.create_user(
            email="Pessoa@EXEMPLO.COM", nome="P", password="x123456789"
        )
        self.assertEqual(u.email, "Pessoa@exemplo.com")

    def test_create_superuser(self):
        su = Usuario.objects.create_superuser(
            email="s@b.com", nome="Sup", password="x123456789"
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.tipo, "admin")

    def test_is_active_reflete_ativo(self):
        u = criar_usuario()
        u.ativo = False
        u.save()
        self.assertFalse(u.is_active)

    def test_str(self):
        u = criar_usuario(email="z@b.com", nome="Zelia")
        self.assertEqual(str(u), "Zelia (z@b.com)")

    def test_email_unico(self):
        criar_usuario(email="dup@b.com")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                criar_usuario(email="dup@b.com", nome="Outro")


# ===========================================================================
# 3. Modelos de dominio
# ===========================================================================
class ModelTests(TestCase):
    def test_estabelecimento_str(self):
        self.assertEqual(str(criar_estabelecimento("Tranca Linda")), "Tranca Linda")

    def test_estabelecimento_usuario_str_e_default(self):
        est = criar_estabelecimento()
        user = criar_usuario()
        vinc = EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        self.assertEqual(vinc.tipo_acesso, "ver")  # default
        self.assertIn(est.nome, str(vinc))
        self.assertIn("ver", str(vinc))

    def test_estabelecimento_usuario_unico(self):
        est = criar_estabelecimento()
        user = criar_usuario()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)

    def test_cliente_str_com_e_sem_apelido(self):
        est = criar_estabelecimento()
        com = Cliente.objects.create(estabelecimento=est, apelido="Bia")
        sem = Cliente.objects.create(estabelecimento=est, apelido="")
        self.assertEqual(str(com), "Bia")
        self.assertEqual(str(sem), str(sem.id))

    def test_cliente_defaults(self):
        est = criar_estabelecimento()
        c = Cliente.objects.create(estabelecimento=est, apelido="Bia")
        self.assertFalse(c.anonimizado)
        self.assertIsNotNone(c.data_cadastro)

    def test_atendimento_str_e_duracao_nullable(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est, duracao=None)
        self.assertIsNone(at.duracao)
        self.assertIn(est.nome, str(at))

    def test_forma_pagamento_str(self):
        self.assertEqual(str(FormaPagamento.objects.create(nome="Pix")), "Pix")

    def test_pagamento_str_sem_forma(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        pag = Pagamento.objects.create(
            atendimento=at, forma_pagamento=None, valor=Decimal("150")
        )
        self.assertIn("sem forma", str(pag))

    def test_pagamento_str_com_forma(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        forma = FormaPagamento.objects.create(nome="Pix")
        pag = Pagamento.objects.create(
            atendimento=at, forma_pagamento=forma, valor=Decimal("150")
        )
        self.assertIn("Pix", str(pag))

    def test_categoria_custo_hierarquia_e_default(self):
        pai = CategoriaCusto.objects.create(nome="Material")
        filho = CategoriaCusto.objects.create(nome="Cabelo", nivel_superior=pai)
        self.assertFalse(pai.vinculado_atendimento)
        self.assertIn(filho, pai.subcategorias.all())
        self.assertEqual(str(filho), "Cabelo")

    def test_custo_str(self):
        est = criar_estabelecimento()
        cat = CategoriaCusto.objects.create(nome="Aluguel")
        custo = Custo.objects.create(
            estabelecimento=est,
            categoria_custo=cat,
            descricao="Junho",
            data=date(2026, 6, 1),
            valor=Decimal("800"),
        )
        self.assertIn("Aluguel", str(custo))
        self.assertIn("800", str(custo))

    def test_caracteristica_ordenacao_e_defaults(self):
        c2 = CaracteristicaAtendimento.objects.create(
            ordem=2, nome="Tamanho", pergunta="Qual?"
        )
        c1 = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        self.assertEqual(
            list(CaracteristicaAtendimento.objects.all()), [c1, c2]
        )  # ordering
        self.assertEqual(c1.numero_maximo_selecao, 1)
        self.assertFalse(c1.contem_dado_sensivel)
        self.assertEqual(str(c1), "Tipo")

    def test_opcao_str_e_hierarquia(self):
        carac = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        pai = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=carac, nome="Box braids"
        )
        filho = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=carac, nome="Fina", nivel_superior=pai
        )
        self.assertIn(filho, pai.subdivisoes.all())
        self.assertIn("Box braids", str(pai))

    def test_atendimento_caracteristica_unico(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        carac = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Qual?"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=carac, nome="Box"
        )
        AtendimentoCaracteristica.objects.create(atendimento=at, opcao=opcao)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AtendimentoCaracteristica.objects.create(atendimento=at, opcao=opcao)


# ===========================================================================
# 4. Regras de exclusao (on_delete)
# ===========================================================================
class ModelDeletionRulesTests(TestCase):
    def test_estabelecimento_protegido_por_atendimento(self):
        est = criar_estabelecimento()
        criar_atendimento(est)
        with self.assertRaises(ProtectedError):
            est.delete()

    def test_cliente_protegido_por_atendimento(self):
        est = criar_estabelecimento()
        cliente = Cliente.objects.create(estabelecimento=est, apelido="Bia")
        criar_atendimento(est, cliente=cliente)
        with self.assertRaises(ProtectedError):
            cliente.delete()

    def test_atendimento_cascateia_pagamento_e_caracteristica(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        Pagamento.objects.create(
            atendimento=at, forma_pagamento=None, valor=Decimal("10")
        )
        carac = CaracteristicaAtendimento.objects.create(
            ordem=1, nome="Tipo", pergunta="Q"
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=carac, nome="Box"
        )
        AtendimentoCaracteristica.objects.create(atendimento=at, opcao=opcao)
        at.delete()
        self.assertEqual(Pagamento.objects.count(), 0)
        self.assertEqual(AtendimentoCaracteristica.objects.count(), 0)

    def test_categoria_pai_set_null_nos_filhos(self):
        pai = CategoriaCusto.objects.create(nome="Material")
        filho = CategoriaCusto.objects.create(nome="Cabelo", nivel_superior=pai)
        pai.delete()
        filho.refresh_from_db()
        self.assertIsNone(filho.nivel_superior)


class AtendimentoCaracteristicaStrTests(TestCase):
    def test_atendimento_caracteristica_str(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="Tipo", pergunta="Q")
        o = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=c, nome="Box"
        )
        ac = AtendimentoCaracteristica.objects.create(atendimento=at, opcao=o)
        self.assertIn("Box", str(ac))


# ===========================================================================
# Ramos de modelos ainda sem teste
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class ModelRamosTests(TestCase):
    def test_custo_clean_rejeita_categoria_raiz(self):
        est = criar_estabelecimento()
        raiz = CategoriaCusto.objects.create(nome="Estrutura")
        custo = Custo(
            estabelecimento=est,
            categoria_custo=raiz,
            descricao="X",
            data=date(2026, 6, 1),
            valor=Decimal("10"),
        )
        with self.assertRaises(ValidationError):
            custo.clean()

    def test_custo_clean_aceita_subcategoria(self):
        est = criar_estabelecimento()
        raiz = CategoriaCusto.objects.create(nome="Estrutura")
        folha = CategoriaCusto.objects.create(nome="Aluguel", nivel_superior=raiz)
        custo = Custo(
            estabelecimento=est,
            categoria_custo=folha,
            descricao="X",
            data=date(2026, 6, 1),
            valor=Decimal("10"),
        )
        custo.clean()  # nao deve levantar

    def test_forma_pagamento_padrao_unica(self):
        a = FormaPagamento.objects.create(nome="Pix", padrao=True)
        b = FormaPagamento.objects.create(nome="Dinheiro", padrao=True)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertFalse(a.padrao)
        self.assertTrue(b.padrao)
