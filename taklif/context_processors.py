"""
Saytning barcha sahifalarida (har bir view alohida qo'shmasdan) kerak
bo'ladigan umumiy ma'lumotlarni shablonlarga uzatadigan context processor'lar.
"""
import os

from django.conf import settings
from django.utils import translation


def til_royxati(request):
    """
    Til tanlash oynasi (dropdown) uchun til ro'yxatini uzatadi.

    MUHIM: Django'ning o'zining {% get_available_languages %} tegi har bir
    til nomini gettext() orqali o'tkazadi — bu esa Django'ning ICHKI
    tarjima kataloglarida ("English" -> "Ingliz tili" kabi) mos yozuv bo'lsa,
    joriy tilga qarab til nomini avtomatik tarjima qilib yuboradi. Natijada
    "English" degan yozuv sayt qaysi tilda ochilganiga qarab har xil bo'lib
    qolar edi (masalan o'zbekchada "Ingliz tili", ruschada "Английский").

    Buning oldini olish uchun bu yerda settings.LANGUAGES ro'yxati hech
    qanday tarjimasiz, xuddi yozilganidek (masalan har doim "English")
    uzatiladi.
    """
    joriy_kod = translation.get_language()
    nomlar = dict(settings.LANGUAGES)
    return {
        "TIL_ROYXATI": settings.LANGUAGES,
        "JORIY_TIL_KODI": joriy_kod,
        "JORIY_TIL_NOMI": nomlar.get(joriy_kod, joriy_kod),
    }


def google_analytics(request):
    """
    Google Analytics 4 (GA4) o'lchov ID'sini shablonlarga uzatadi.

    .env faylida GOOGLE_ANALYTICS_ID=G-XXXXXXXXXX ko'rinishida qo'yiladi.
    Agar bu qiymat bo'sh bo'lsa, base.html shablonidagi GA skripti
    umuman chiqarilmaydi (masalan, lokal development muhitida).
    """
    return {
        "GOOGLE_ANALYTICS_ID": os.environ.get("GOOGLE_ANALYTICS_ID", ""),
    }
