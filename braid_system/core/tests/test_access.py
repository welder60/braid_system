"""Autorizacao centralizada (core/access.py) e context processor."""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase, override_settings

from braid_system.core.access import (
    get_estabelecimento_ativo,
    pode_acessar_estabelecimento,
    usuario_vinculado,
)
from braid_system.core.context_processors import estabelecimento_ativo
from braid_system.core.models import (
    EstabelecimentoUsuario,
)

from .utils import (
    HASHERS_RAPIDOS,
    criar_estabelecimento,
    criar_usuario,
)


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


class ContextProcessorExtraTests(TestCase):
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


# ===========================================================================
# access.py — ramos de borda
# ===========================================================================
@override_settings(PASSWORD_HASHERS=HASHERS_RAPIDOS)
class AccessUnitTests(TestCase):
    def test_usuario_vinculado_estabelecimento_none(self):
        user = criar_usuario()
        self.assertFalse(usuario_vinculado(user, None))

    def test_usuario_vinculado_anonimo(self):
        est = criar_estabelecimento()
        self.assertFalse(usuario_vinculado(AnonymousUser(), est))

    def test_pode_acessar_estabelecimento_anonimo(self):
        est = criar_estabelecimento()
        self.assertFalse(pode_acessar_estabelecimento(AnonymousUser(), est))

    def test_get_estabelecimento_ativo_request_sem_user(self):
        req = RequestFactory().get("/")
        self.assertIsNone(get_estabelecimento_ativo(req))

    def test_get_estabelecimento_ativo_admin_sem_auto_select(self):
        # Admin sem selecao explicita nao recebe auto-selecao.
        admin = criar_usuario(email="adm@b.com", tipo="admin")
        criar_estabelecimento()
        req = RequestFactory().get("/")
        req.user = admin
        req.session = {}
        self.assertIsNone(get_estabelecimento_ativo(req, auto_select=True))
