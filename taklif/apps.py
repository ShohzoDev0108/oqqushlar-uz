from django.apps import AppConfig
from axes.apps import AppConfig as _AxesAppConfig


class TaklifConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "taklif"
    verbose_name = "Taklifnomalar"


class OqqushlarAxesConfig(_AxesAppConfig):
    """django-axes uchun o'z AppConfig'imiz.

    Bu paket (INSTALLED_APPS'dagi "axes") o'z tarjima katalogini
    ta'minlamaydi va boshqaruv panelidagi bo'lim nomini ("Axes") tarjima
    funksiyasidan o'tkazmasdan qat'iy belgilaydi — shu sababli uni oddiy
    .po tarjimasi orqali o'zgartirib bo'lmaydi. Shu bo'limni o'zbekcha
    ko'rsatish uchun paketning o'z ilova konfiguratsiyasini shu klass bilan
    (faqat verbose_name'ni almashtirib) kengaytiramiz — qolgan hammasi
    (ready(), initialize() va h.k.) asl axes.apps.AppConfig'dan meros
    bo'lib qoladi (settings.py'dagi INSTALLED_APPS'ga qarang).
    """

    verbose_name = "Xavfsizlik nazorati"
