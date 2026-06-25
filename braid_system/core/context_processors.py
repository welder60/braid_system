from .access import get_estabelecimento_ativo


def estabelecimento_ativo(request):
    """Injeta o estabelecimento ativo (ja autorizado) na sessao.

    A resolucao e delegada a braid_system.core.access.get_estabelecimento_ativo,
    que garante que apenas estabelecimentos vinculados (ou qualquer um, no caso
    de admin) sejam considerados. Mantem a auto-selecao quando ha um unico
    vinculo, preservando a experiencia anterior.
    """
    if not request.user.is_authenticated:
        return {}
    return {'estabelecimento_ativo': get_estabelecimento_ativo(request, auto_select=True)}
