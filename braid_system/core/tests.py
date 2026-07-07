"""
Suite de testes do Braid System (app core + app security).

Organizacao:
    - HelperFunctionTests ......... funcoes utilitarias puras de views.py
    - UsuarioModelTests ........... modelo de autenticacao e UsuarioManager
    - ModelTests .................. modelos de dominio (__str__, defaults, relacoes)
    - ModelDeletionRulesTests ..... regras on_delete (PROTECT / CASCADE / SET_NULL)
    - ContextProcessorTests ....... estabelecimento_ativo
    - UrlRoutingTests ............. resolucao/reverse das URLs nomeadas
    - AuthFlowTests ............... login / logout / protecao de rotas
    - EstabelecimentoViewTests .... CRUD de estabelecimentos
    - CategoriaCustoViewTests ..... CRUD de categorias (hierarquia)
    - CaracteristicaViewTests ..... CRUD de caracteristicas e opcoes
    - UsuarioViewTests ............ CRUD de usuarios (painel admin)
    - AcessoViewTests ............. CRUD de vinculos usuario/estabelecimento
    - ClienteViewTests ............ CRUD de clientes (multi-tenant)
    - AtendimentoViewTests ........ fluxo completo de atendimento (+ pagamento/custos)
    - CustoViewTests .............. CRUD de custos avulsos (filtro mes/ano)

Rodar com:  python manage.py test braid_system.core
"""

from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import resolve, reverse

from braid_system.core import views
from braid_system.core.context_processors import estabelecimento_ativo
from braid_system.core.models import (
    Atendimento,
    AtendimentoCaracteristica,
    CaracteristicaAtendimento,
    CaracteristicaAtendimentoOpcao,
    CategoriaCusto,
    Cliente,
    Custo,
    Estabelecimento,
    EstabelecimentoUsuario,
    FormaPagamento,
    Pagamento,
)

Usuario = get_user_model()


# ---------------------------------------------------------------------------
# Helpers de criacao reutilizados pelos testes
# ---------------------------------------------------------------------------
def criar_usuario(
    email="pro@exemplo.com",
    nome="Profissional",
    senha="testuser-abc-987654",
    tipo="profissional",
    **extra,
):
    return Usuario.objects.create_user(
        email=email, nome=nome, password=senha, tipo=tipo, **extra
    )


def criar_estabelecimento(nome="Salao da Tati"):
    return Estabelecimento.objects.create(nome=nome)


def criar_atendimento(estabelecimento, cliente=None, **extra):
    if cliente is None:
        cliente = Cliente.objects.create(
            estabelecimento=estabelecimento, apelido="Cliente X"
        )
    defaults = dict(data=date(2026, 6, 1), hora=time(14, 30), duracao=90)
    defaults.update(extra)
    return Atendimento.objects.create(
        estabelecimento=estabelecimento, cliente=cliente, **defaults
    )


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


# ===========================================================================
# 5. Context processor estabelecimento_ativo
# ===========================================================================
class ContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _req(self, user, session=None):
        req = self.factory.get("/")
        req.user = user
        req.session = {} if session is None else session
        return req

    def test_anonimo_retorna_vazio(self):
        ctx = estabelecimento_ativo(self._req(AnonymousUser()))
        self.assertEqual(ctx, {})

    def test_session_valida_retorna_estabelecimento(self):
        est = criar_estabelecimento()
        user = criar_usuario()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        req = self._req(user, {"estabelecimento_ativo_id": str(est.pk)})
        self.assertEqual(estabelecimento_ativo(req)["estabelecimento_ativo"], est)

    def test_auto_selecao_quando_unico_vinculo(self):
        est = criar_estabelecimento()
        user = criar_usuario()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        req = self._req(user)
        ctx = estabelecimento_ativo(req)
        self.assertEqual(ctx["estabelecimento_ativo"], est)
        self.assertEqual(
            req.session["estabelecimento_ativo_id"], str(est.pk)
        )  # persistiu

    def test_multiplos_vinculos_sem_selecao_retorna_none(self):
        user = criar_usuario()
        for nome in ("A", "B"):
            EstabelecimentoUsuario.objects.create(
                estabelecimento=criar_estabelecimento(nome), usuario=user
            )
        ctx = estabelecimento_ativo(self._req(user))
        self.assertIsNone(ctx["estabelecimento_ativo"])


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


# ===========================================================================
# 7. Autenticacao e protecao de rotas
# ===========================================================================
class AuthFlowTests(TestCase):
    def setUp(self):
        self.senha = "senha-de-teste-123456"
        self.user = criar_usuario(senha=self.senha)

    def test_home_publica(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_login_get_redireciona_home(self):
        self.assertRedirects(self.client.get(reverse("login")), reverse("home"))

    def test_login_valido(self):
        resp = self.client.post(
            reverse("login"), {"username": self.user.email, "password": self.senha}
        )
        # Login leva a gestao; usuario sem vinculo e encaminhado ao onboarding.
        self.assertRedirects(
            resp, reverse("gestao"), target_status_code=302
        )
        self.assertEqual(int(self.client.session["_auth_user_id"] != ""), 1)

    def test_login_invalido(self):
        resp = self.client.post(
            reverse("login"), {"username": self.user.email, "password": "errada"}
        )
        self.assertRedirects(resp, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("logout")), reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_rotas_protegidas_anonimo_redirecionam(self):
        for nome in ["perfil", "atendimentos", "custos", "clientes", "relatorios"]:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("home"))

    def test_post_protegido_anonimo_redireciona(self):
        self.assertRedirects(
            self.client.post(reverse("atendimento_criar"), {}), reverse("home")
        )


# ===========================================================================
# Mixin: cliente autenticado com estabelecimento ativo na sessao
# ===========================================================================
class AutenticadoComEstabelecimentoMixin:
    def setUp(self):
        super().setUp()
        self.user = criar_usuario()
        self.est = criar_estabelecimento("Salao Principal")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=self.est, usuario=self.user, tipo_acesso="administrar"
        )
        self.client.force_login(self.user)
        sessao = self.client.session
        sessao["estabelecimento_ativo_id"] = str(self.est.pk)
        sessao.save()


class AdminLogadoMixin:
    """Loga um usuario tipo='admin' (o painel administrativo exige admin)."""

    def setUp(self):
        super().setUp()
        self.admin = criar_usuario(
            email="admin-painel@b.com", nome="Admin Painel", tipo="admin"
        )
        self.client.force_login(self.admin)


# ===========================================================================
# 8. CRUD de estabelecimentos
# ===========================================================================
class EstabelecimentoViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        criar_estabelecimento("A")
        self.assertEqual(self.client.get(reverse("estabelecimentos")).status_code, 200)

    def test_criar_valido(self):
        resp = self.client.post(
            reverse("estabelecimento_criar"), {"nome": "Novo Salao"}
        )
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertTrue(Estabelecimento.objects.filter(nome="Novo Salao").exists())

    def test_criar_nome_vazio_nao_cria(self):
        resp = self.client.post(reverse("estabelecimento_criar"), {"nome": "   "})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Estabelecimento.objects.count(), 0)

    def test_editar(self):
        est = criar_estabelecimento("Antigo")
        resp = self.client.post(
            reverse("estabelecimento_editar", args=[est.pk]), {"nome": "Renovado"}
        )
        self.assertRedirects(resp, reverse("estabelecimentos"))
        est.refresh_from_db()
        self.assertEqual(est.nome, "Renovado")

    def test_excluir(self):
        est = criar_estabelecimento("Para Excluir")
        resp = self.client.post(reverse("estabelecimento_excluir", args=[est.pk]))
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertFalse(Estabelecimento.objects.filter(pk=est.pk).exists())

    def test_excluir_protegido_redireciona_com_erro(self):
        est = criar_estabelecimento("Com Atendimento")
        criar_atendimento(est)
        resp = self.client.post(reverse("estabelecimento_excluir", args=[est.pk]))
        self.assertRedirects(resp, reverse("estabelecimentos"))
        self.assertTrue(Estabelecimento.objects.filter(pk=est.pk).exists())
        msgs = [str(m) for m in resp.wsgi_request._messages]
        self.assertTrue(any("Não é possível excluir" in m for m in msgs))

    def test_editar_inexistente_404(self):
        import uuid

        resp = self.client.post(
            reverse("estabelecimento_editar", args=[uuid.uuid4()]), {"nome": "x"}
        )
        self.assertEqual(resp.status_code, 404)

    def test_pagina_publica_cadastro(self):
        self.assertEqual(
            self.client.get(reverse("cadastro_estabelecimento")).status_code, 200
        )
        resp = self.client.post(
            reverse("cadastro_estabelecimento"), {"nome": "Via Cadastro"}
        )
        self.assertRedirects(resp, reverse("cadastro_estabelecimento"))
        self.assertTrue(Estabelecimento.objects.filter(nome="Via Cadastro").exists())


# ===========================================================================
# 9. CRUD de categorias de custo
# ===========================================================================
class CategoriaCustoViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("categorias_custo")).status_code, 200)

    def test_criar_com_flag_vinculado(self):
        resp = self.client.post(
            reverse("categoria_custo_criar"),
            {"nome": "Material", "vinculado_atendimento": "on"},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat = CategoriaCusto.objects.get(nome="Material")
        self.assertTrue(cat.vinculado_atendimento)

    def test_criar_subcategoria(self):
        pai = CategoriaCusto.objects.create(nome="Pai")
        resp = self.client.post(
            reverse("categoria_custo_criar"),
            {"nome": "Filha", "nivel_superior": str(pai.pk)},
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        self.assertEqual(CategoriaCusto.objects.get(nome="Filha").nivel_superior, pai)

    def test_criar_sem_nome(self):
        resp = self.client.post(reverse("categoria_custo_criar"), {"nome": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CategoriaCusto.objects.count(), 0)

    def test_editar(self):
        cat = CategoriaCusto.objects.create(nome="Velho")
        resp = self.client.post(
            reverse("categoria_custo_editar", args=[cat.pk]), {"nome": "Novo"}
        )
        self.assertRedirects(resp, reverse("categorias_custo"))
        cat.refresh_from_db()
        self.assertEqual(cat.nome, "Novo")

    def test_excluir(self):
        cat = CategoriaCusto.objects.create(nome="X")
        resp = self.client.post(reverse("categoria_custo_excluir", args=[cat.pk]))
        self.assertRedirects(resp, reverse("categorias_custo"))
        self.assertEqual(CategoriaCusto.objects.count(), 0)


# ===========================================================================
# 10. CRUD de caracteristicas e suas opcoes
# ===========================================================================
class CaracteristicaViewTests(AdminLogadoMixin, TestCase):
    def test_criar_valido(self):
        resp = self.client.post(
            reverse("caracteristica_atendimento_criar"),
            {
                "nome": "Tipo",
                "pergunta": "Qual tipo?",
                "ordem": "1",
                "numero_maximo_selecao": "2",
                "contem_dado_sensivel": "on",
            },
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        c = CaracteristicaAtendimento.objects.get(nome="Tipo")
        self.assertEqual(c.numero_maximo_selecao, 2)
        self.assertTrue(c.contem_dado_sensivel)

    def test_criar_faltando_campos(self):
        resp = self.client.post(
            reverse("caracteristica_atendimento_criar"), {"nome": "Tipo"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CaracteristicaAtendimento.objects.count(), 0)

    def test_editar(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        resp = self.client.post(
            reverse("caracteristica_atendimento_editar", args=[c.pk]),
            {"nome": "B", "pergunta": "Q2", "ordem": "3"},
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        c.refresh_from_db()
        self.assertEqual((c.nome, c.ordem), ("B", 3))

    def test_excluir(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="A", pergunta="Q")
        resp = self.client.post(
            reverse("caracteristica_atendimento_excluir", args=[c.pk])
        )
        self.assertRedirects(resp, reverse("caracteristicas_atendimento"))
        self.assertEqual(CaracteristicaAtendimento.objects.count(), 0)

    def test_opcoes_crud(self):
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="Tipo", pergunta="Q")
        # listar
        self.assertEqual(
            self.client.get(
                reverse("caracteristica_atendimento_opcoes", args=[c.pk])
            ).status_code,
            200,
        )
        # criar
        resp = self.client.post(
            reverse("opcao_caracteristica_criar", args=[c.pk]), {"nome": "Box braids"}
        )
        self.assertRedirects(
            resp, reverse("caracteristica_atendimento_opcoes", args=[c.pk])
        )
        opcao = CaracteristicaAtendimentoOpcao.objects.get(nome="Box braids")
        # criar subopcao
        self.client.post(
            reverse("opcao_caracteristica_criar", args=[c.pk]),
            {"nome": "Fina", "nivel_superior": str(opcao.pk)},
        )
        self.assertEqual(
            CaracteristicaAtendimentoOpcao.objects.get(nome="Fina").nivel_superior,
            opcao,
        )
        # editar
        self.client.post(
            reverse("opcao_caracteristica_editar", args=[c.pk, opcao.pk]),
            {"nome": "Box braids G"},
        )
        opcao.refresh_from_db()
        self.assertEqual(opcao.nome, "Box braids G")
        # excluir
        resp = self.client.post(
            reverse("opcao_caracteristica_excluir", args=[c.pk, opcao.pk])
        )
        self.assertRedirects(
            resp, reverse("caracteristica_atendimento_opcoes", args=[c.pk])
        )


# ===========================================================================
# 11. CRUD de usuarios (painel admin)
# ===========================================================================
class UsuarioViewTests(AdminLogadoMixin, TestCase):
    def test_listar(self):
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 200)

    def test_criar_valido(self):
        resp = self.client.post(
            reverse("usuario_criar"),
            {
                "nome": "Nova",
                "email": "nova@b.com",
                "tipo": "profissional",
                "password": "senha123456",
            },
        )
        self.assertRedirects(resp, reverse("usuarios"))
        self.assertTrue(Usuario.objects.filter(email="nova@b.com").exists())

    def test_criar_email_duplicado(self):
        criar_usuario(email="dup@b.com")
        resp = self.client.post(
            reverse("usuario_criar"),
            {
                "nome": "X",
                "email": "dup@b.com",
                "tipo": "profissional",
                "password": "senha123456",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Usuario.objects.filter(email="dup@b.com").count(), 1)

    def test_criar_campos_faltando(self):
        resp = self.client.post(reverse("usuario_criar"), {"nome": "X"})
        self.assertEqual(resp.status_code, 200)
        # admin logado ja conta como 1 usuario; garantimos que o alvo nao foi criado
        self.assertFalse(Usuario.objects.filter(nome="X").exists())

    def test_editar_desativa(self):
        u = criar_usuario(email="e@b.com", nome="Edita")
        resp = self.client.post(
            reverse("usuario_editar", args=[u.pk]),
            {"nome": "Editada", "tipo": "gerente", "ativo": "0"},
        )
        self.assertRedirects(resp, reverse("usuarios"))
        u.refresh_from_db()
        self.assertEqual(u.nome, "Editada")
        self.assertEqual(u.tipo, "gerente")
        self.assertFalse(u.ativo)

    def test_excluir(self):
        u = criar_usuario(email="x@b.com")
        resp = self.client.post(reverse("usuario_excluir", args=[u.pk]))
        self.assertRedirects(resp, reverse("usuarios"))
        self.assertFalse(Usuario.objects.filter(pk=u.pk).exists())


# ===========================================================================
# 12. CRUD de acessos (vinculo usuario <-> estabelecimento)
# ===========================================================================
class AcessoViewTests(TestCase):
    def setUp(self):
        self.admin = criar_usuario(email="admin@b.com", nome="Admin", tipo="admin")
        self.client.force_login(self.admin)
        self.est = criar_estabelecimento("Est A")
        self.alvo = criar_usuario(email="alvo@b.com", nome="Alvo")

    def test_listar(self):
        self.assertEqual(
            self.client.get(reverse("acessos_estabelecimento")).status_code, 200
        )

    def test_criar_registra_incluido_por(self):
        resp = self.client.post(
            reverse("acesso_criar"),
            {
                "usuario": str(self.alvo.pk),
                "estabelecimento": str(self.est.pk),
                "tipo_acesso": "editar",
            },
        )
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        vinc = EstabelecimentoUsuario.objects.get(
            usuario=self.alvo, estabelecimento=self.est
        )
        self.assertEqual(vinc.tipo_acesso, "editar")
        self.assertEqual(vinc.incluido_por, self.admin)

    def test_criar_duplicado(self):
        EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        resp = self.client.post(
            reverse("acesso_criar"),
            {
                "usuario": str(self.alvo.pk),
                "estabelecimento": str(self.est.pk),
                "tipo_acesso": "ver",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 1)

    def test_criar_campos_faltando(self):
        resp = self.client.post(reverse("acesso_criar"), {"usuario": str(self.alvo.pk)})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 0)

    def test_editar_tipo_acesso(self):
        vinc = EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est, tipo_acesso="ver"
        )
        resp = self.client.post(
            reverse("acesso_editar", args=[vinc.pk]), {"tipo_acesso": "administrar"}
        )
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        vinc.refresh_from_db()
        self.assertEqual(vinc.tipo_acesso, "administrar")

    def test_excluir(self):
        vinc = EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        resp = self.client.post(reverse("acesso_excluir", args=[vinc.pk]))
        self.assertRedirects(resp, reverse("acessos_estabelecimento"))
        self.assertEqual(EstabelecimentoUsuario.objects.count(), 0)

    def test_filtro_por_estabelecimento(self):
        outro = criar_estabelecimento("Est B")
        EstabelecimentoUsuario.objects.create(
            usuario=self.alvo, estabelecimento=self.est
        )
        EstabelecimentoUsuario.objects.create(usuario=self.alvo, estabelecimento=outro)
        resp = self.client.get(
            reverse("acessos_estabelecimento"), {"estabelecimento": str(self.est.pk)}
        )
        self.assertEqual(resp.context["total_acessos"], 1)


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
# 16. Cobertura adicional: perfil, formularios de edicao (GET) e ramos
# ===========================================================================
class PerfilViewTests(TestCase):
    def setUp(self):
        self.user = criar_usuario()
        self.est = criar_estabelecimento("Meu Salao")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=self.est, usuario=self.user
        )
        self.client.force_login(self.user)

    def test_get_lista_estabelecimentos(self):
        resp = self.client.get(reverse("perfil"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.est, resp.context["estabelecimentos_usuario"])

    def test_post_seleciona_estabelecimento_valido(self):
        resp = self.client.post(
            reverse("perfil"), {"estabelecimento_id": str(self.est.pk)}
        )
        self.assertRedirects(resp, reverse("perfil"))
        self.assertEqual(
            self.client.session["estabelecimento_ativo_id"], str(self.est.pk)
        )

    def test_post_estabelecimento_invalido(self):
        import uuid

        # Segundo vinculo evita a auto-selecao do context processor (so ocorre com 1 vinculo),
        # isolando a rejeicao do id invalido pela view perfil.
        outro = criar_estabelecimento("Outro Salao")
        EstabelecimentoUsuario.objects.create(estabelecimento=outro, usuario=self.user)
        resp = self.client.post(
            reverse("perfil"), {"estabelecimento_id": str(uuid.uuid4())}
        )
        self.assertRedirects(resp, reverse("perfil"))
        self.assertNotIn("estabelecimento_ativo_id", self.client.session)


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


class ExtraBranchTests(TestCase):
    def test_context_processor_session_invalida_cai_para_vinculo(self):
        import uuid

        user = criar_usuario()
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        req = RequestFactory().get("/")
        req.user = user
        req.session = {"estabelecimento_ativo_id": str(uuid.uuid4())}  # id inexistente
        ctx = estabelecimento_ativo(req)
        self.assertEqual(ctx["estabelecimento_ativo"], est)

    def test_atendimento_caracteristica_str(self):
        est = criar_estabelecimento()
        at = criar_atendimento(est)
        c = CaracteristicaAtendimento.objects.create(ordem=1, nome="Tipo", pergunta="Q")
        o = CaracteristicaAtendimentoOpcao.objects.create(
            caracteristica_atendimento=c, nome="Box"
        )
        ac = AtendimentoCaracteristica.objects.create(atendimento=at, opcao=o)
        self.assertIn("Box", str(ac))


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


# ===========================================================================
# 17. Isolamento de estabelecimentos (requisito de seguranca)
# ===========================================================================
class AdminPainelAcessoTests(TestCase):
    """Painel administrativo: somente tipo='admin' acessa."""

    ROTAS = [
        "admin_painel",
        "estabelecimentos",
        "usuarios",
        "acessos_estabelecimento",
        "categorias_custo",
        "caracteristicas_atendimento",
        "formas_pagamento",
    ]

    def test_anonimo_redireciona_para_home(self):
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("home"))

    def test_profissional_redireciona_para_gestao(self):
        user = criar_usuario(email="pro2@b.com", tipo="profissional")
        # Vincula a um estabelecimento para que /gestao/ resolva (200) e nao
        # dispare o redirecionamento de onboarding ao seguir o redirect.
        EstabelecimentoUsuario.objects.create(
            estabelecimento=criar_estabelecimento("Est Pro2"), usuario=user
        )
        self.client.force_login(user)
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertRedirects(self.client.get(reverse(nome)), reverse("gestao"))

    def test_consultor_nao_e_admin(self):
        # Decisao do time: 'consultor' NAO bypassa a restricao de estabelecimentos.
        user = criar_usuario(email="cons@b.com", tipo="consultor")
        EstabelecimentoUsuario.objects.create(
            estabelecimento=criar_estabelecimento("Est Cons"), usuario=user
        )
        self.client.force_login(user)
        self.assertRedirects(
            self.client.get(reverse("estabelecimentos")), reverse("gestao")
        )
        self.assertRedirects(
            self.client.get(reverse("acessos_estabelecimento")), reverse("gestao")
        )

    def test_admin_acessa_todas_as_rotas(self):
        self.client.force_login(criar_usuario(email="adm@b.com", tipo="admin"))
        for nome in self.ROTAS:
            with self.subTest(rota=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)


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


class OnboardingEstabelecimentoTests(TestCase):
    """Primeiro login: usuario sem vinculo cria e e vinculado ao estabelecimento."""

    def test_get_exibe_form_para_usuario_sem_vinculo(self):
        self.client.force_login(criar_usuario(email="novo@b.com", tipo="profissional"))
        resp = self.client.get(reverse("onboarding_estabelecimento"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, "core/onboarding_estabelecimento.html")

    def test_post_cria_estabelecimento_e_vincula_como_administrar(self):
        user = criar_usuario(email="dono@b.com", tipo="profissional")
        self.client.force_login(user)
        resp = self.client.post(
            reverse("onboarding_estabelecimento"), {"nome": "Studio da Ana"}
        )
        self.assertRedirects(resp, reverse("gestao"))
        est = Estabelecimento.objects.get(nome="Studio da Ana")
        vinc = EstabelecimentoUsuario.objects.get(usuario=user, estabelecimento=est)
        self.assertEqual(vinc.tipo_acesso, "administrar")
        self.assertEqual(vinc.incluido_por, user)
        # Estabelecimento fica ativo na sessao.
        self.assertEqual(
            self.client.session.get("estabelecimento_ativo_id"), str(est.pk)
        )

    def test_post_nome_vazio_nao_cria_nada(self):
        user = criar_usuario(email="vazio@b.com", tipo="profissional")
        self.client.force_login(user)
        resp = self.client.post(reverse("onboarding_estabelecimento"), {"nome": "  "})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(EstabelecimentoUsuario.objects.filter(usuario=user).exists())

    def test_usuario_ja_vinculado_e_redirecionado_para_gestao(self):
        user = criar_usuario(email="temvinc@b.com", tipo="profissional")
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        self.client.force_login(user)
        resp = self.client.get(reverse("onboarding_estabelecimento"))
        self.assertRedirects(resp, reverse("gestao"))

    def test_gestao_redireciona_usuario_sem_vinculo_para_onboarding(self):
        self.client.force_login(criar_usuario(email="semvinc@b.com", tipo="profissional"))
        resp = self.client.get(reverse("gestao"))
        self.assertRedirects(resp, reverse("onboarding_estabelecimento"))

    def test_admin_nao_precisa_de_onboarding(self):
        self.client.force_login(criar_usuario(email="adm@b.com", tipo="admin"))
        resp = self.client.get(reverse("gestao"))
        self.assertEqual(resp.status_code, 200)
