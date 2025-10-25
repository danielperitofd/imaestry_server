from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("musicas/", include("musicas.urls")),
    path("accounts/", include("allauth.urls")),
    path("", lambda request: redirect("musicas:welcome")),  # ← redireciona raiz para tela de boas-vindas
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
