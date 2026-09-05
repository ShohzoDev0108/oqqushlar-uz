# -*- coding: utf-8 -*-
"""Ochib ko'rish mumkin bo'lgan NAMUNA taklifnomalar.

NEGA BAZADA EMAS. Namuna — sotuv sahifasi, mijoz yozuvi emas. Agar u
Taklifnoma jadvalida haqiqiy qator bo'lganda edi, "Mening
taklifnomalarim", statistika, limitlar va zaxira nusxa — hammasi uni
mijoz taklifnomasi deb hisoblardi, va bundan keyin yoziladigan har bir
so'rovda `.exclude(...)` turishi kerak bo'lardi. Bitta joyda unutilsa —
sezilmaydigan xato.

Shablonlar `taklifnoma` obyektidan FAQAT oddiy maydonlarni oladi
(tekshirilgan: birorta bog'liq jadval ham, `pk` ham ishlatilmaydi),
shuning uchun xotirada yasalgan, SAQLANMAGAN Taklifnoma butunlay
yetarli.

TILAKLAR. Namunadagi RSVP formasi ishlaydi, lekin javob bazaga emas,
mijozning O'Z sessiyasiga yoziladi va faqat o'ziga ko'rsatiladi.
Sababi: haqiqiy taklifnomada tilak mezbon tasdiqlagandan keyingina
ommaga ko'rinadi (`RSVP.tilak_tasdiqlangan`, `views.tilak_tasdiqlash`).
Namunada mezbon yo'q — demak yo tilak umuman ko'rinmaydi (mijoz nima
bo'lganini tushunmaydi), yo uni avtomatik tasdiqlaymiz va sotuv
sahifamizda moderatsiyasiz, ochiq izoh maydoni paydo bo'ladi. Sessiya
ikkalasidan ham qutqaradi: mijoz o'zi yozganini darhol ko'radi,
boshqa hech kim ko'rmaydi.
"""

from datetime import timedelta
from types import SimpleNamespace

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import MAROSIM_DASTUR_NAMUNALARI, Taklifnoma

# Namuna marosimi shuncha kundan keyin bo'ladi — sanoq bloki ("qoldi:
# 45 kun") jonli ishlashi va "marosim o'tib ketgan" holatiga tushmasligi
# uchun sana har doim kelajakda hisoblanadi, qat'iy yozilmaydi.
NAMUNA_KUN_QOSHIMCHA = 45

# Mijozning o'z tilagi shu kalit ostida sessiyada saqlanadi.
SESSIYA_KALITI = "namuna_tilaklari"
# Bitta brauzerda saqlanadigan eng ko'p namuna tilagi (har bir dizayn
# uchun bittadan). Cheklov sessiya cookie'si cheksiz o'smasligi uchun.
SESSIYADA_MAKS = 12

# Har bir marosim turi uchun namuna mazmuni. Ismlar va matnlar —
# o'zimizniki, hech qayerdan ko'chirilmagan.
MAROSIM_NAMUNALARI = {
    "toy": {
        "ismlar": ("Aziz", "Malika", ""),
        "toyxona": _("Bahor to'yxonasi"),
        "manzil": _("Toshkent shahri, Chilonzor tumani, Bunyodkor shoh ko'chasi 12"),
        "matn": _(
            "Hayotimizning eng baxtli kunini biz uchun eng qadrli "
            "insonlar bilan birga nishonlamoqchimiz. Kelishingizni "
            "sabrsizlik bilan kutamiz."
        ),
        "kiyim_kodi": _("Bayramona"),
        "imzo": _("Kelin-kuyov nomidan"),
        "sovga_karta": "8600 0000 0000 0000",
    },
    "fotiha_toy": {
        "ismlar": ("Sanjar", "Nilufar", ""),
        "toyxona": _("Oila davrasi"),
        "manzil": _("Samarqand shahri, Registon ko'chasi 4"),
        "matn": _(
            "Ikki oilaning qo'shilishi — bir umrlik quvonch. Shu "
            "quvonchli kunda duo va oq yo'l tilaklaringiz biz uchun "
            "eng qimmatli sovg'a bo'ladi."
        ),
        "kiyim_kodi": _("Bosiq, ochiq ranglar"),
        "imzo": _("Ikki oila nomidan"),
        "sovga_karta": "",
    },
    "qizlar_bazmi": {
        "ismlar": ("Zilola", "", ""),
        "toyxona": _("Nilufar bog'i"),
        "manzil": _("Farg'ona shahri, Mustaqillik ko'chasi 27"),
        "matn": _(
            "Qizimizni oq yo'l bilan kuzatayotgan kunimizda yonimizda "
            "bo'lsangiz, quvonchimiz ikki barobar bo'ladi."
        ),
        "kiyim_kodi": _("Milliy yoki bayramona"),
        "imzo": _("Qiz ota-onasi nomidan"),
        "sovga_karta": "",
    },
    "sunnat_toy": {
        "ismlar": ("Amirbek", "Sardorbek", ""),
        "toyxona": _("Chinor to'yxonasi"),
        "manzil": _("Buxoro shahri, Navoiy ko'chasi 8"),
        "matn": _(
            "Farzandlarimiz hayotidagi muhim kunni yaqinlarimiz bilan "
            "birga o'tkazishni istaymiz. Marhamat, tashrif buyuring."
        ),
        "kiyim_kodi": _("Bayramona"),
        "imzo": _("Ota-ona nomidan"),
        "sovga_karta": "",
    },
    "beshik_toy": {
        "ismlar": ("Oysha", "", ""),
        "toyxona": _("Oila hovlisi"),
        "manzil": _("Andijon shahri, Bog'ishamol ko'chasi 15"),
        "matn": _(
            "Xonadonimizga quvonch olib kirgan kichkintoyimizning "
            "beshik to'yiga sizni chin dildan taklif qilamiz."
        ),
        "kiyim_kodi": "",
        "imzo": _("Ota-ona va buvi-bobolar nomidan"),
        "sovga_karta": "",
    },
    "nahor_oshi": {
        "ismlar": ("Rustam", "", ""),
        "toyxona": _("Do'stlik oshxonasi"),
        "manzil": _("Namangan shahri, Amir Temur ko'chasi 3"),
        "matn": _(
            "Ertalabki oshimizga marhamat qiling. Sizni davramizda "
            "ko'rish biz uchun katta sharaf."
        ),
        "kiyim_kodi": "",
        "imzo": _("Rustamovlar oilasi nomidan"),
        "sovga_karta": "",
    },
    "yubiley": {
        "ismlar": ("Gulchehra", "", ""),
        "toyxona": _("Zamin restorani"),
        "manzil": _("Toshkent shahri, Yunusobod tumani, Amir Temur shox ko'chasi 108"),
        "matn": _(
            "Onamizning tavallud sanasini eng yaqin insonlar davrasida "
            "nishonlamoqchimiz. Iliq so'zlaringiz bilan bu kunni "
            "bezashingizni so'raymiz."
        ),
        "kiyim_kodi": _("Rasmiy"),
        "imzo": _("Farzandlar va nabiralar nomidan"),
        "sovga_karta": "8600 0000 0000 0000",
    },
    "tugilgan_kun": {
        "ismlar": ("Diyorbek", "", ""),
        "toyxona": _("Bolalar quvonch markazi"),
        "manzil": _("Qarshi shahri, Nasaf ko'chasi 21"),
        "matn": _(
            "O'g'limiz yetti yoshga to'lyapti. Uning quvonchini "
            "do'stlari va yaqinlari bilan birga bo'lishishni istaymiz."
        ),
        "kiyim_kodi": _("Erkin"),
        "imzo": _("Ota-ona nomidan"),
        "sovga_karta": "",
    },
    "boshqa": {
        "ismlar": ("", "", ""),
        "boshqa_tadbir_nomi": _("Bitiruv kechasi"),
        "toyxona": _("Maktab yig'inlar zali"),
        "manzil": _("Nukus shahri, Do'stlik ko'chasi 6"),
        "matn": _(
            "O'n bir yillik yo'limiz yakuniga yetdi. Shu unutilmas "
            "kechani birga o'tkazaylik."
        ),
        "kiyim_kodi": _("Rasmiy"),
        "imzo": _("Bitiruvchilar nomidan"),
        "sovga_karta": "",
    },
}

# Namuna tilaklari — bo'lim bo'sh va jonsiz ko'rinmasligi uchun. Har bir
# marosimga o'z ohangida.
NAMUNA_TILAKLARI = {
    "toy": [
        (_("Dilnoza"), _("Umringiz uzoq, dasturxoningiz doim to'kin bo'lsin!")),
        (_("Bekzod"), _("Ikkalangizga ham sabr, ham baxt tilayman. Qutlug' bo'lsin!")),
    ],
    "fotiha_toy": [
        (_("Nodira opa"), _("Oq yo'l! Ikki oilaga tinchlik va totuvlik tilaymiz.")),
    ],
    "qizlar_bazmi": [
        (_("Shahnoza"), _("Yangi xonadoningda faqat quvonch ko'r, singlim.")),
    ],
    "sunnat_toy": [
        (_("Anvar amaki"), _("Bolalar sog' bo'lsin, ota-onaga quvonch keltirsin!")),
    ],
    "beshik_toy": [
        (_("Ozoda"), _("Beshigi bo'sh qolmasin, farzandingiz baxtli bo'lsin.")),
    ],
    "nahor_oshi": [
        (_("Jahongir"), _("Oshingiz halol, davrangiz keng bo'lsin!")),
    ],
    "yubiley": [
        (_("Kamola"), _("Sog'liq va tinchlik tilaymiz. Yana ko'p yillar shunday!")),
    ],
    "tugilgan_kun": [
        (_("Sevinch"), _("Katta yigit bo'l, o'qishing zo'r bo'lsin!")),
    ],
    "boshqa": [
        (_("Sinfdosh"), _("Yo'lingiz ochiq bo'lsin, do'stlar. Uchrashib turaylik!")),
    ],
}

# Xarita tugmasi ham ishlab tursin — namunada Toshkent markazi
# ko'rsatiladi (aniq manzil emas, shunchaki tugma ishlashini ko'rsatish
# uchun).
NAMUNA_XARITA = "https://maps.google.com/?q=41.311081,69.240562"


def marosim_tanlash(shablon, sorovdagi_tur=""):
    """Namuna qaysi marosim turida ochilishini hal qiladi.

    Dizaynlar endi marosimga qarab boshqacha ochiladi (parda, shakl,
    ranglar), shuning uchun namuna ham "qandaydir" emas, aynan shu
    dizaynga biriktirilgan marosimda ko'rsatilishi kerak.
    """
    ruxsat = shablon.marosim_turlari or []
    if sorovdagi_tur and (not ruxsat or sorovdagi_tur in ruxsat):
        if sorovdagi_tur in MAROSIM_NAMUNALARI:
            return sorovdagi_tur
    if not ruxsat:
        return "toy"
    # Dizayn bir nechta marosimga mos bo'lsa, eng ko'p uchraydigani
    # ("Nikoh to'yi") ustun turadi; bo'lmasa ro'yxatdagi birinchisi.
    if "toy" in ruxsat:
        return "toy"
    for tur in ruxsat:
        if tur in MAROSIM_NAMUNALARI:
            return tur
    return "toy"


def _namuna_sanasi(dastur):
    """Namuna sanasi — bugundan NAMUNA_KUN_QOSHIMCHA kun keyin.

    Vaqti kun tartibining birinchi bandidan olinadi: nahor oshi 06:30 da,
    to'y esa 17:30 da boshlanadi — namunada ham shunday ko'rinsin.
    """
    soat, daqiqa = 18, 0
    if dastur:
        try:
            soat, daqiqa = (int(q) for q in str(dastur[0]["vaqt"]).split(":"))
        except (ValueError, KeyError, TypeError):
            pass
    hozir = timezone.localtime(timezone.now())
    return (hozir + timedelta(days=NAMUNA_KUN_QOSHIMCHA)).replace(
        hour=soat, minute=daqiqa, second=0, microsecond=0
    )


def namuna_taklifnomasi(shablon, marosim_turi, musiqa_variant=None):
    """SAQLANMAGAN Taklifnoma qaytaradi — faqat ko'rsatish uchun.

    DIQQAT: bu obyekt hech qachon .save() qilinmaydi. Uni bazaga
    yozadigan kod yozilib qolsa, namuna mijoz taklifnomalari orasiga
    aralashib ketadi — modul boshidagi izohga qarang.
    """
    malumot = MAROSIM_NAMUNALARI.get(marosim_turi, MAROSIM_NAMUNALARI["toy"])
    ism_1, ism_2, ism_3 = malumot["ismlar"]
    dastur = MAROSIM_DASTUR_NAMUNALARI.get(marosim_turi, [])
    taklifnoma = Taklifnoma(
        marosim_turi=marosim_turi,
        ism_1=str(ism_1),
        ism_2=str(ism_2),
        ism_3=str(ism_3),
        boshqa_tadbir_nomi=str(malumot.get("boshqa_tadbir_nomi", "")),
        # Slug faqat ko'rsatish uchun — bu manzil bo'yicha hech narsa
        # ochilmaydi, RSVP formasi esa alohida manzilga yuboriladi
        # (views.namuna dagi "rsvp_manzili").
        slug=f"namuna-{shablon.kod}",
        shablon=shablon,
        sana=_namuna_sanasi(dastur),
        toyxona=str(malumot["toyxona"]),
        manzil=str(malumot["manzil"]),
        xarita_link=NAMUNA_XARITA,
        matn=str(malumot["matn"]),
        kiyim_kodi=str(malumot["kiyim_kodi"]),
        imzo=str(malumot["imzo"]),
        dastur=[
            {"vaqt": b["vaqt"], "nom": str(b["nom"]), "izoh": str(b.get("izoh", ""))}
            for b in dastur
        ],
        sovga_karta=malumot["sovga_karta"],
        musiqa_variant=musiqa_variant,
        # To'langan deb ko'rsatiladi — aks holda shablon "hali
        # faollashtirilmagan" bannerini va mijoz panelini chizadi
        # (_mijoz_qismi.html), bu esa namunada o'rinsiz.
        tolangan=True,
        faol=True,
    )
    return taklifnoma


def tayyor_tilaklar(marosim_turi):
    """Namunada ko'rsatiladigan, oldindan yozilgan tilaklar."""
    juftliklar = NAMUNA_TILAKLARI.get(marosim_turi, NAMUNA_TILAKLARI["toy"])
    return [
        SimpleNamespace(ism=str(ism), tilak=str(tilak), oziniki=False)
        for ism, tilak in juftliklar
    ]


def _sessiya_lugati(request):
    lugat = request.session.get(SESSIYA_KALITI)
    return lugat if isinstance(lugat, dict) else {}


def sessiyadagi_tilak(request, shablon_kod):
    """Shu brauzer shu dizayn namunasiga yozgan tilak (bo'lsa)."""
    yozuv = _sessiya_lugati(request).get(shablon_kod)
    if not isinstance(yozuv, dict) or not yozuv.get("tilak"):
        return None
    return SimpleNamespace(
        ism=yozuv.get("ism", ""), tilak=yozuv["tilak"], oziniki=True
    )


def sessiyaga_tilak_yoz(request, shablon_kod, ism, tilak):
    """Tilakni FAQAT shu brauzer sessiyasiga yozadi — bazaga emas."""
    lugat = _sessiya_lugati(request)
    lugat[shablon_kod] = {"ism": ism, "tilak": tilak}
    if len(lugat) > SESSIYADA_MAKS:
        # Eng eski yozuvlarni tashlab yuboramiz (dict Python 3.7+ da
        # qo'shilish tartibini saqlaydi).
        ortiqcha = len(lugat) - SESSIYADA_MAKS
        for kalit in list(lugat)[:ortiqcha]:
            lugat.pop(kalit, None)
    request.session[SESSIYA_KALITI] = lugat
    request.session.modified = True
