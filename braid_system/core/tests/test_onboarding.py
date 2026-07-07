"""Onboarding: criacao do primeiro estabelecimento do usuario."""

from django.test import TestCase
from django.urls import reverse

from braid_system.core.models import (
    Estabelecimento,
    EstabelecimentoUsuario,
)

from .utils import (
    criar_estabelecimento,
    criar_usuario,
)


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
        self.client.force_login(
            criar_usuario(email="semvinc@b.com", tipo="profissional")
        )
        resp = self.client.get(reverse("gestao"))
        self.assertRedirects(resp, reverse("onboarding_estabelecimento"))

    def test_admin_nao_precisa_de_onboarding(self):
        self.client.force_login(criar_usuario(email="adm@b.com", tipo="admin"))
        resp = self.client.get(reverse("gestao"))
        self.assertEqual(resp.status_code, 200)
