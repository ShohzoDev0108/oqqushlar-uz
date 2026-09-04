"""
Saytning barcha sahifalarida (har bir view alohida qo'shmasdan) kerak
bo'ladigan umumiy ma'lumotlarni shablonlarga uzatadigan context processor'lar.
"""
import os

from django.conf import settings
from django.utils import translation


# Til tugmasida ko'rsatiladigan qisqa belgilar.
#
# Nega ikki emas, uch harfli variantlar ham bor: sayt tillari orasida
# uchta turkiy til bor (Qozoq, Qirg'iz, Qoraqalpoq) — ikki harfda ular
# bir-biriga o'xshab, chalkashtiradi ("QQ" qaysi biri?). Uch harf bu
# muammoni yechadi. Ro'yxatda esa har doim TO'LIQ nom ko'rinadi, ya'ni
# qisqartma hech qachon yagona ma'lumot manbai bo'lib qolmaydi.
#
# Har bir belgi shu tilning O'Z alifbosida yozilgan — foydalanuvchi o'z
# tilini boshqa til imlosida emas, o'zi tanigan shaklda ko'radi.
TIL_QISQA = {
    "uz": "O'Z",
    "ru": "РУ",
    "en": "EN",
    "tg": "ТОҶ",
    "kk": "ҚАЗ",
    "ky": "КЫР",
    "tk": "TÜR",
    "kaa": "QRQ",
}


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
    # (kod, to'liq nom, qisqa belgi) — qisqa belgi faqat tugmaning
    # o'zida ko'rsatiladi, ro'yxatda esa to'liq nom qoladi.
    royxat = [(kod, nom, TIL_QISQA.get(kod, kod.upper())) for kod, nom in settings.LANGUAGES]
    return {
        "TIL_ROYXATI": royxat,
        "JORIY_TIL_KODI": joriy_kod,
        "JORIY_TIL_NOMI": nomlar.get(joriy_kod, joriy_kod),
        "JORIY_TIL_QISQA": TIL_QISQA.get(joriy_kod, (joriy_kod or "").upper()),
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


def aloqa(request):
    """Aloqa kanallari — barcha sahifalarda (footerda) kerak.

    Har bir view'ga alohida qo'shish o'rniga shu yerda beriladi: kanallar
    footerda turadi, footer esa hamma joyda. Qiymatlar admin panelidan
    o'zgartiriladi (SaytSozlamalari), ya'ni raqamni almashtirish uchun
    deploy qilish shart emas.

    SaytSozlamalari.olish() keshlangan — bu context processor har bir
    so'rovda ishlagani uchun keshsiz bo'lsa, har bir tashrifga bitta
    ortiqcha bazaga so'rov qo'shilardi.
    """
    from .models import SaytSozlamalari

    sozlama = SaytSozlamalari.olish()
    return {
        "ALOQA_TELEGRAM": (sozlama.admin_telegram or settings.SAYT_ADMIN_TELEGRAM or "").lstrip("@"),
        "ALOQA_TELEFON": sozlama.telefon,
        "ALOQA_TELEFON_RAQAMI": sozlama.telefon_raqami,
        "ALOQA_INSTAGRAM": sozlama.instagram_nomi,
    }
