from .models import Estabelecimento, EstabelecimentoUsuario


def estabelecimento_ativo(request):
    """Injeta o estabelecimento atualmente selecionado na sessão."""
    if not request.user.is_authenticated:
        return {}

    est_id = request.session.get('estabelecimento_ativo_id')
    if est_id:
        try:
            est = Estabelecimento.objects.get(pk=est_id)
            return {'estabelecimento_ativo': est}
        except Estabelecimento.DoesNotExist:
            pass

    # Tenta definir automaticamente se houver apenas um vínculo
    vinculos = EstabelecimentoUsuario.objects.filter(
        usuario=request.user
    ).select_related('estabelecimento')

    if vinculos.count() == 1:
        est = vinculos.first().estabelecimento
        request.session['estabelecimento_ativo_id'] = str(est.pk)
        return {'estabelecimento_ativo': est}

    return {'estabelecimento_ativo': None}
