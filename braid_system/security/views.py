"""
Views de autenticação social (Login com Google / OpenID Connect).

Fluxo (Authorization Code + OIDC):
  1. ``google_login``   -> redireciona o usuário para a tela de consentimento
                           do Google guardando state/nonce na sessão.
  2. ``google_callback`` -> recebe o retorno do Google, troca o code por tokens,
                           valida o id_token e autentica (ou cria) o Usuario.
"""
from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.shortcuts import redirect
from django.urls import reverse

from .models import Usuario
from .oauth import oauth, google_oauth_configured

# Como autenticamos sem chamar authenticate(), informamos o backend ao login().
AUTH_BACKEND = 'django.contrib.auth.backends.ModelBackend'


def google_login(request):
    """Inicia o fluxo OAuth2 redirecionando para o Google."""
    if not google_oauth_configured():
        messages.error(
            request, 'O login com Google ainda não está configurado.'
        )
        return redirect('home')

    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    return oauth.google.authorize_redirect(request, redirect_uri)


def google_callback(request):
    """Recebe o retorno do Google, valida e autentica o usuário."""
    if not google_oauth_configured():
        messages.error(
            request, 'O login com Google ainda não está configurado.'
        )
        return redirect('home')

    # Troca o "code" pelos tokens e valida o id_token (assinatura/nonce).
    try:
        token = oauth.google.authorize_access_token(request)
    except OAuthError:
        messages.error(
            request, 'Não foi possível concluir o login com Google. '
                     'Tente novamente.'
        )
        return redirect('home')

    # Com escopo OpenID, o Authlib disponibiliza as claims em token['userinfo'].
    userinfo = token.get('userinfo') or {}
    email = (userinfo.get('email') or '').strip()
    email_verificado = bool(userinfo.get('email_verified'))
    nome = (userinfo.get('name') or '').strip()

    if not email or not email_verificado:
        messages.error(
            request, 'Sua conta Google não retornou um e-mail verificado.'
        )
        return redirect('home')

    if not nome:
        nome = email.split('@')[0]

    # Busca case-insensitive para não duplicar contas já cadastradas.
    user = Usuario.objects.filter(email__iexact=email).first()
    if user is None:
        # Primeiro login: provisiona a conta com o papel padrão.
        user = Usuario(
            email=email,
            nome=nome,
            tipo=settings.GOOGLE_OAUTH_DEFAULT_TIPO,
        )
        # Conta sem senha local: só acessa via Google.
        user.set_unusable_password()
        user.save()

    if not user.ativo:
        messages.error(
            request, 'Sua conta está inativa. Procure um administrador.'
        )
        return redirect('home')

    auth_login(request, user, backend=AUTH_BACKEND)
    return redirect('gestao')
