"""Login/logout, protecao de rotas, home por tipo de usuario e perfil."""

from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import (
    EstabelecimentoUsuario,
)

from .utils import (
    HASHERS_RAPIDOS,
    AdminLogadoMixin,
    criar_estabelecimento,
    criar_usuario,
)


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
        self.assertRedirects(resp, reverse("gestao"), target_status_code=302)
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

    def test_rotas_de_escrita_anonimo_redirecionam(self):
        import uuid

        pk = uuid.uuid4()
        rotas = [
            ("atendimento_editar", [pk]),
            ("atendimento_excluir", [pk]),
            ("custo_criar", []),
            ("custo_editar", [pk]),
            ("custo_excluir", [pk]),
            ("cliente_criar", []),
            ("cliente_editar", [pk]),
            ("cliente_excluir", [pk]),
        ]
        for nome, args in rotas:
            with self.subTest(rota=nome):
                resp = self.client.post(reverse(nome, args=args), {})
                self.assertRedirects(resp, reverse("home"))


# ===========================================================================
# Home — redirecionamento por tipo de usuario
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class HomeRedirectTests(TestCase):
    def test_admin_vai_para_admin_painel(self):
        self.client.force_login(criar_usuario(email="a@b.com", tipo="admin"))
        self.assertRedirects(self.client.get(reverse("home")), reverse("admin_painel"))

    def test_consultor_vai_para_consultor_painel(self):
        consultor = criar_usuario(email="c@b.com", tipo="consultor")
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=consultor)
        self.client.force_login(consultor)
        self.assertRedirects(
            self.client.get(reverse("home")), reverse("consultor_painel")
        )

    def test_profissional_vai_para_gestao(self):
        user = criar_usuario()
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=user)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("home")), reverse("gestao"))


class SobreViewTests(TestCase):
    def test_pagina_publica(self):
        self.assertEqual(self.client.get(reverse("sobre")).status_code, 200)


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


# ===========================================================================
# Perfil do admin — lista todos os estabelecimentos
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class PerfilAdminTests(AdminLogadoMixin, TestCase):
    def test_admin_ve_todos_os_estabelecimentos(self):
        criar_estabelecimento("Alfa")
        criar_estabelecimento("Beta")
        resp = self.client.get(reverse("perfil"))
        self.assertEqual(resp.status_code, 200)
        nomes = [e.nome for e in resp.context["estabelecimentos_usuario"]]
        self.assertEqual(nomes, ["Alfa", "Beta"])

    def test_admin_seleciona_estabelecimento_sem_vinculo(self):
        est = criar_estabelecimento("Alfa")
        resp = self.client.post(reverse("perfil"), {"estabelecimento_id": est.pk})
        self.assertRedirects(resp, reverse("perfil"))
        self.assertEqual(self.client.session["estabelecimento_ativo_id"], str(est.pk))
