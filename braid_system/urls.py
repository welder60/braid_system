"""URL configuration for braid_system project.

https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("braid_system.security.urls")),
    path("", include("braid_system.core.urls")),
]

# Admin embutido do Django: por padrão só é montado em desenvolvimento, pois a
# tela de login (/admin/) fica exposta publicamente e nenhum modelo do app está
# registrado nele. Em produção, habilite via DJANGO_ADMIN_ENABLED e, de
# preferência, sirva-o numa URL secreta definida em DJANGO_ADMIN_URL (veja
# settings.py / .env.example). O acesso continua exigindo is_staff=True.
if settings.DJANGO_ADMIN_ENABLED:
    from django.contrib import admin

    urlpatterns.insert(0, path(settings.DJANGO_ADMIN_URL, admin.site.urls))

# Em desenvolvimento, o Django serve os arquivos de mídia locais.
# Em produção os uploads são servidos diretamente pelo Supabase Storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
