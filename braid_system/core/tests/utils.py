"""Helpers e mixins compartilhados pela suite de testes."""

from datetime import date, time

from django.contrib.auth import get_user_model

from braid_system.core.models import (
    Atendimento,
    Cliente,
    Estabelecimento,
    EstabelecimentoUsuario,
)

Usuario = get_user_model()

# Hasher rapido: os testes nao validam a forca do hash de senha.
HASHERS_RAPIDOS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


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
