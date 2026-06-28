"""
Autorizacao centralizada de acesso a estabelecimentos.

Requisito de seguranca:
    Um usuario so pode ver/manipular dados de estabelecimentos aos quais esta
    vinculado (modelo EstabelecimentoUsuario). A UNICA excecao e o
    administrador (tipo == 'admin'), que enxerga todos os estabelecimentos.

Toda decisao de "qual estabelecimento este usuario pode acessar" passa por
aqui, para evitar divergencias entre views, context processors e templates.
"""

from .models import Estabelecimento, EstabelecimentoUsuario

# Apenas o papel 'admin' tem visao irrestrita dos estabelecimentos.
# (O papel 'consultor' NAO e considerado administrador para fins de
# isolamento de dados — ver decisao registrada com o time.)
TIPO_ADMIN = "admin"


def is_admin(user):
    """True se o usuario autenticado e administrador (visao irrestrita)."""
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "tipo", None) == TIPO_ADMIN
    )


def usuario_vinculado(user, estabelecimento):
    """True se existe vinculo (EstabelecimentoUsuario) entre user e estabelecimento."""
    if estabelecimento is None or not getattr(user, "is_authenticated", False):
        return False
    return EstabelecimentoUsuario.objects.filter(
        usuario=user, estabelecimento=estabelecimento
    ).exists()


def pode_acessar_estabelecimento(user, estabelecimento):
    """
    Regra mestra de autorizacao:
    admin acessa qualquer estabelecimento; os demais, apenas os vinculados.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if is_admin(user):
        return True
    return usuario_vinculado(user, estabelecimento)


def get_estabelecimento_ativo(request, auto_select=False):
    """
    Resolve o estabelecimento ativo da sessao APLICANDO autorizacao.

    - Le 'estabelecimento_ativo_id' da sessao e so devolve o estabelecimento
      se o usuario puder acessa-lo (admin ou vinculado). Caso contrario, o id
      e descartado da sessao (defesa contra sessao "presa" apos revogacao de
      acesso ou manipulacao indevida).
    - Com auto_select=True (uso no context processor), se um usuario NAO-admin
      tiver exatamente um vinculo, seleciona-o automaticamente e persiste na
      sessao. As views de dados usam auto_select=False de proposito: sem
      selecao explicita, nada e exibido.
    """
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    est_id = request.session.get("estabelecimento_ativo_id")
    if est_id:
        est = Estabelecimento.objects.filter(pk=est_id).first()
        if est is not None and pode_acessar_estabelecimento(user, est):
            return est
        # id inexistente, invalido ou nao autorizado: nao confiar nele.
        request.session.pop("estabelecimento_ativo_id", None)

    if auto_select and not is_admin(user):
        vinculos = EstabelecimentoUsuario.objects.filter(usuario=user).select_related(
            "estabelecimento"
        )
        if vinculos.count() == 1:
            est = vinculos.first().estabelecimento
            request.session["estabelecimento_ativo_id"] = str(est.pk)
            return est

    return None
