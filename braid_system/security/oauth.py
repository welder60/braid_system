"""
Registro do cliente OAuth2 do Google (OpenID Connect) via Authlib.

O objeto ``oauth`` é compartilhado pelas views de autenticação. A descoberta
dos endpoints (authorization, token, jwks, userinfo) é feita automaticamente
a partir do documento de metadados do Google, então não precisamos fixar URLs.
"""

from authlib.integrations.django_client import OAuth
from django.conf import settings

# Documento de descoberta OpenID Connect do Google.
GOOGLE_CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"

oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url=GOOGLE_CONF_URL,
    client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
    client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
    client_kwargs={
        # openid+email+profile dá acesso ao e-mail verificado e ao nome.
        "scope": "openid email profile",
    },
)


def google_oauth_configured():
    """Retorna True somente se as credenciais do Google estão presentes."""
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)
