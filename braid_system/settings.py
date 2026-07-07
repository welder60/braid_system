"""
Django settings for braid_system project.

Configuração por ambiente, controlada pela variável DEBUG:

  DEBUG=True   -> Desenvolvimento: SQLite local + arquivos de mídia em media/
  DEBUG=False  -> Produção:        PostgreSQL (Supabase) + Supabase Storage (S3)

As variáveis de ambiente podem ser definidas no sistema (Railway, etc.) ou,
em desenvolvimento, num arquivo .env na raiz do projeto. Veja .env.example.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/
"""

import logging
import os
import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key

import dj_database_url
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de um arquivo .env (conveniência em desenvolvimento).
# Em produção as variáveis normalmente vêm do próprio ambiente.
load_dotenv(BASE_DIR / ".env")


# --------------------------------------------------------------------------- #
# Helpers para ler variáveis de ambiente                                      #
# --------------------------------------------------------------------------- #
def env_bool(name, default=False):
    """Lê uma variável de ambiente como booleano."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=None):
    """Lê uma variável separada por vírgulas como lista de strings."""
    value = os.environ.get(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]


def env_required(name):
    """Lê uma variável obrigatória; erro claro se ausente (produção)."""
    value = os.environ.get(name)
    if not value:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            f"A variável de ambiente obrigatória '{name}' não está definida. "
            f"Defina-a no ambiente de produção (ou no arquivo .env)."
        )
    return value


# --------------------------------------------------------------------------- #
# Ambiente                                                                     #
# --------------------------------------------------------------------------- #
# DEBUG é o interruptor entre desenvolvimento e produção.
# Padrão seguro: assume produção (False) quando a variável não está definida.
DEBUG = env_bool("DEBUG", default=False)

# SECURITY WARNING: keep the secret key used in production secret!
if DEBUG:
    # Em desenvolvimento, gera uma chave aleatória se a variável não estiver definida.
    # Para sessões estáveis (ex.: manter login entre reinicios), defina SECRET_KEY no .env.
    SECRET_KEY = os.environ.get("SECRET_KEY") or get_random_secret_key()
else:
    # Em produção, a chave é obrigatória e deve vir do ambiente.
    SECRET_KEY = env_required("SECRET_KEY")

ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    default=(
        ["127.0.0.1", "localhost"]
        if DEBUG
        else ["braidsystem-development.up.railway.app"]
    ),
)

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    default=([] if DEBUG else ["https://braidsystem-development.up.railway.app"]),
)


# --------------------------------------------------------------------------- #
# Application definition                                                       #
# --------------------------------------------------------------------------- #
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "braid_system.core.apps.CoreConfig",
    "braid_system.security.apps.SecurityConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serve os arquivos estáticos em produção (logo após Security).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "braid_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "braid_system.core.context_processors.estabelecimento_ativo",
            ],
        },
    },
]

WSGI_APPLICATION = "braid_system.wsgi.application"


# --------------------------------------------------------------------------- #
# Database                                                                     #
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases               #
# --------------------------------------------------------------------------- #
if DEBUG:
    # Desenvolvimento: SQLite local.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Produção: PostgreSQL (Supabase) a partir de DATABASE_URL.
    DATABASES = {
        "default": dj_database_url.parse(
            env_required("DATABASE_URL"),
            conn_max_age=600,
            ssl_require=True,
        )
    }
    # O pooler do Supabase (Supavisor) em modo de transação não suporta
    # cursores no servidor; desabilitamos para evitar erros.
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True


# --------------------------------------------------------------------------- #
# Password validation                                                          #
# --------------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Durante os testes, usa um hasher de senha rápido: o PBKDF2 (padrão) torna a
# suíte MUITO mais lenta sem ganho algum de segurança em ambiente de teste.
# Prática recomendada na documentação oficial do Django ("Speeding up tests").
if len(sys.argv) > 1 and sys.argv[1] == "test":
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


# --------------------------------------------------------------------------- #
# Internationalization                                                         #
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# --------------------------------------------------------------------------- #
# Static & Media files / Storages                                             #
# https://docs.djangoproject.com/en/6.0/ref/settings/#storages                #
# --------------------------------------------------------------------------- #
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# URL base de mídia (usada pelo FileSystemStorage em desenvolvimento).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if DEBUG:
    # Desenvolvimento: arquivos enviados e estáticos no disco local.
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    # Produção: uploads no Supabase Storage (API S3) e estáticos via WhiteNoise.
    SUPABASE_STORAGE_BUCKET = env_required("SUPABASE_STORAGE_BUCKET")
    SUPABASE_S3_ENDPOINT = env_required("SUPABASE_S3_ENDPOINT")
    # URL pública do projeto, ex.: https://<ref>.supabase.co
    _supabase_public_url = env_required("SUPABASE_PROJECT_URL").rstrip("/")
    _supabase_public_host = _supabase_public_url.split("://", 1)[-1]

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": SUPABASE_STORAGE_BUCKET,
                "endpoint_url": SUPABASE_S3_ENDPOINT,
                "region_name": os.environ.get("SUPABASE_S3_REGION", "us-east-1"),
                "access_key": env_required("SUPABASE_S3_ACCESS_KEY_ID"),
                "secret_key": env_required("SUPABASE_S3_SECRET_ACCESS_KEY"),
                # Supabase exige endereçamento path-style (bucket no caminho).
                "addressing_style": "path",
                "file_overwrite": False,
                # Bucket público: servimos URLs públicas, sem assinatura.
                "querystring_auth": False,
                "custom_domain": (
                    f"{_supabase_public_host}"
                    f"/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}"
                ),
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# Não falhar se um arquivo estático referenciado não estiver no manifesto.
WHITENOISE_MANIFEST_STRICT = False


# --------------------------------------------------------------------------- #
# Segurança em produção (atrás do proxy TLS do Railway/Supabase)              #
# --------------------------------------------------------------------------- #
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


# --------------------------------------------------------------------------- #
# Auth                                                                         #
# --------------------------------------------------------------------------- #
AUTH_USER_MODEL = "security.Usuario"

# Para onde o @login_required redireciona e o destino padrão pós-login.
LOGIN_URL = "home"
LOGIN_REDIRECT_URL = "gestao"
LOGOUT_REDIRECT_URL = "home"

# --------------------------------------------------------------------------- #
# Admin embutido do Django                                                    #
# --------------------------------------------------------------------------- #
# A tela de login do admin (/admin/) fica exposta publicamente e nenhum modelo
# do app está registrado nele, então por padrão ele só é montado em
# desenvolvimento. Em produção, habilite explicitamente (DJANGO_ADMIN_ENABLED=
# True) e, de preferência, sirva-o numa URL secreta (DJANGO_ADMIN_URL=
# algo-dificil-de-adivinhar/). O acesso continua exigindo is_staff=True, ou
# seja, apenas superusuários.
DJANGO_ADMIN_ENABLED = env_bool("DJANGO_ADMIN_ENABLED", default=DEBUG)
DJANGO_ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "admin/").lstrip("/")

# --------------------------------------------------------------------------- #
# Login com Google (OAuth2 / OpenID Connect)                                  #
# --------------------------------------------------------------------------- #
# Credenciais obtidas em https://console.cloud.google.com/apis/credentials
# (OAuth 2.0 Client ID, tipo "Web application"). Configure a URI de redirect
# autorizada como  <SEU_DOMINIO>/auth/google/callback/
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

# Tipo (papel) atribuído a um usuário criado automaticamente no 1º login Google.
GOOGLE_OAUTH_DEFAULT_TIPO = os.environ.get(
    "GOOGLE_OAUTH_DEFAULT_TIPO",
    "profissional",
)


# --------------------------------------------------------------------------- #
# Logging estruturado (stdout)                                                 #
# --------------------------------------------------------------------------- #
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {process:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            # Em produção, formato detalhado; em desenvolvimento, simples.
            "formatter": "simple" if DEBUG else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Todos os módulos do projeto herdam este logger.
        "braid_system": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}


# --------------------------------------------------------------------------- #
# Sentry (error tracking em produção)                                          #
# --------------------------------------------------------------------------- #
# Defina SENTRY_DSN no ambiente para ativar. Em desenvolvimento, deixe vazio  #
# (ou omita) para não enviar eventos ao Sentry.                                #
_SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if _SENTRY_DSN:
    import sentry_sdk  # noqa: PLC0415
    from sentry_sdk.integrations.django import DjangoIntegration  # noqa: PLC0415
    from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: PLC0415

    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            # Captura automaticamente logs de ERROR ou acima como eventos Sentry.
            LoggingIntegration(
                level=logging.INFO,  # registra breadcrumbs a partir de INFO
                event_level=logging.ERROR,  # cria evento Sentry a partir de ERROR
            ),
        ],
        traces_sample_rate=float(
            os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0" if DEBUG else "0.1")
        ),
        profiles_sample_rate=float(
            os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.0")
        ),
        environment="development" if DEBUG else "production",
        # Não enviar dados pessoais (IPs, sessões) por padrão.
        send_default_pii=False,
        # Versão do release (opcional: preencha via CI com o commit hash).
        release=os.environ.get("GIT_COMMIT", None),
    )
