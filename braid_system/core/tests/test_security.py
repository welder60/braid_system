"""
Testes do app security — login social com Google (OAuth2 / OpenID Connect).

As chamadas de rede do Authlib sao substituidas por mocks: os testes cobrem a
logica das views (provisionamento, conta inativa, e-mail nao verificado etc.)
sem depender do Google.

Organizacao:
    - OAuthConfiguradoTests ..... helper google_oauth_configured
    - GoogleLoginTests .......... inicio do fluxo (redirect ao Google)
    - GoogleCallbackTests ....... retorno do Google (token -> usuario logado)

Rodar com:  python manage.py test braid_system.core
"""

from unittest import mock

from authlib.integrations.base_client import OAuthError
from django.test import TestCase, override_settings
from django.urls import reverse

from braid_system.core.models import EstabelecimentoUsuario
from .utils import HASHERS_RAPIDOS, criar_estabelecimento, criar_usuario
from braid_system.security.models import Usuario
from braid_system.security.oauth import google_oauth_configured


OAUTH_CONFIGURADO = {
    "GOOGLE_OAUTH_CLIENT_ID": "client-id-teste",
    "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret-teste",
    "GOOGLE_OAUTH_DEFAULT_TIPO": "profissional",
}


def _token_google(
    email="nova@exemplo.com", nome="Nova Usuaria", verificado=True, **extra
):
    userinfo = {"email": email, "email_verified": verificado, "name": nome}
    userinfo.update(extra)
    return {"userinfo": userinfo}


# ===========================================================================
# Helper de configuracao
# ===========================================================================
class OAuthConfiguradoTests(TestCase):
    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_sem_credenciais(self):
        self.assertFalse(google_oauth_configured())

    @override_settings(**OAUTH_CONFIGURADO)
    def test_com_credenciais(self):
        self.assertTrue(google_oauth_configured())


# ===========================================================================
# Inicio do fluxo
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class GoogleLoginTests(TestCase):
    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_nao_configurado_redireciona_home(self):
        resp = self.client.get(reverse("google_login"))
        self.assertRedirects(resp, reverse("home"))

    @override_settings(**OAUTH_CONFIGURADO)
    def test_configurado_redireciona_para_o_google(self):
        from django.shortcuts import redirect

        with mock.patch(
            "braid_system.security.views.oauth.google.authorize_redirect",
            return_value=redirect("https://accounts.google.com/o/oauth2/auth"),
        ) as m:
            resp = self.client.get(reverse("google_login"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("accounts.google.com", resp["Location"])
        redirect_uri = m.call_args.args[1]
        self.assertIn(reverse("google_callback"), redirect_uri)


# ===========================================================================
# Retorno do Google
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS, **OAUTH_CONFIGURADO)
class GoogleCallbackTests(TestCase):
    URL_TOKEN = "braid_system.security.views.oauth.google.authorize_access_token"

    def _callback(self, token=None, side_effect=None):
        patcher = mock.patch(
            self.URL_TOKEN, return_value=token, side_effect=side_effect
        )
        with patcher:
            return self.client.get(reverse("google_callback"))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_nao_configurado_redireciona_home(self):
        resp = self.client.get(reverse("google_callback"))
        self.assertRedirects(resp, reverse("home"))

    def test_erro_oauth_redireciona_home_com_mensagem(self):
        resp = self._callback(side_effect=OAuthError())
        self.assertRedirects(resp, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_email_nao_verificado_e_rejeitado(self):
        resp = self._callback(_token_google(verificado=False))
        self.assertRedirects(resp, reverse("home"))
        self.assertEqual(Usuario.objects.count(), 0)

    def test_sem_email_e_rejeitado(self):
        resp = self._callback({"userinfo": {"email_verified": True}})
        self.assertRedirects(resp, reverse("home"))
        self.assertEqual(Usuario.objects.count(), 0)

    def test_primeiro_login_provisiona_usuario_e_vai_para_onboarding(self):
        resp = self._callback(_token_google())
        self.assertRedirects(resp, reverse("onboarding_estabelecimento"))

        user = Usuario.objects.get(email="nova@exemplo.com")
        self.assertEqual(user.nome, "Nova Usuaria")
        from django.conf import settings

        self.assertEqual(user.tipo, settings.GOOGLE_OAUTH_DEFAULT_TIPO)
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_nome_ausente_usa_prefixo_do_email(self):
        resp = self._callback(_token_google(email="ana.silva@exemplo.com", nome=""))
        self.assertEqual(resp.status_code, 302)
        user = Usuario.objects.get(email="ana.silva@exemplo.com")
        self.assertEqual(user.nome, "ana.silva")

    def test_usuario_existente_nao_e_duplicado_case_insensitive(self):
        existente = criar_usuario(email="maria@exemplo.com", nome="Maria")
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=existente)

        resp = self._callback(_token_google(email="MARIA@exemplo.com", nome="Maria G"))
        self.assertRedirects(resp, reverse("gestao"))
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(self.client.session["_auth_user_id"], str(existente.pk))

    def test_conta_inativa_nao_loga(self):
        criar_usuario(email="inativa@exemplo.com", ativo=False)
        resp = self._callback(_token_google(email="inativa@exemplo.com"))
        self.assertRedirects(resp, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_com_vinculo_vai_para_gestao(self):
        existente = criar_usuario(email="pro@exemplo.com")
        est = criar_estabelecimento()
        EstabelecimentoUsuario.objects.create(estabelecimento=est, usuario=existente)
        resp = self._callback(_token_google(email="pro@exemplo.com"))
        self.assertRedirects(resp, reverse("gestao"))
