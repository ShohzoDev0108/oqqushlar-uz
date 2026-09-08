"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from taklif.sitemaps import SAYT_XARITALARI

urlpatterns = [
    # Manzil standart "admin/" emas — settings.ADMIN_URL_YOLI orqali
    # sozlanadi (.env'da DJANGO_ADMIN_MANZILI) — botlar avtomatik taxmin
    # qila olmasligi uchun.
    path(settings.ADMIN_URL_YOLI, admin.site.urls),
    # Til almashtirish (masalan taklifnoma sahifasidagi til tugmasi shu yerga POST qiladi).
    # taklif.urls'dagi umumiy "<slug:slug>/" kabi qoidalardan oldin turishi shart.
    path("i18n/", include("django.conf.urls.i18n")),
    # Qidiruv tizimlari uchun. Ikkalasi ham "taklif.urls" dan OLDIN
    # turishi shart — u yerdagi umumiy "<slug:slug>/" qoidasi bo'lmasa
    # ham, tartib aniq bo'lgani yaxshi.
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SAYT_XARITALARI},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
    path("", include("taklif.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
