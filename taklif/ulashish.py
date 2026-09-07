# -*- coding: utf-8 -*-
"""Har bir taklifnoma uchun ULASHISH KARTOCHKASI (og:image) yasaydi.

MUAMMO. Mijoz taklifnoma havolasini Telegramda 50-100 mehmonga yuboradi.
Havola ostida chiqadigan oldindan ko'rinish (preview) esa hammasida bir xil
edi — bizning umumiy `og-rasm.png` logotipimiz. Ya'ni mehmon "Sardor va
Malika" emas, "Oqqushlar" degan reklama ko'rardi; taklifnoma o'zi haqida
hech narsa aytmasdi. Mijoz uchun mahsulot aynan shu ko'rinishdan boshlanadi.

YECHIM. Serverda, so'rov paytida 1200x630 rasm chiziladi: marosim nomi,
ismlar, sana va o'sha DIZAYNNING o'z ranglari. Mijoz foto yuklagan bo'lsa,
foto fon bo'lib qoladi (yumshatilgan va dizayn rangida pardalangan holda) —
lekin ustida baribir ismlar va sana yoziladi, chunki Telegram fotoni o'z
nisbatida qirqadi va yozuvsiz foto hech qanday ma'lumot bermaydi.

NEGA SERVERDA CHIZILADI, tayyor fayl saqlanmaydi. Mijoz ismini yoki sanani
tahrirlashi mumkin; saqlangan fayl bo'lsa, uni har bir tahrirdan keyin
qayta yasash va eskisini o'chirish kerak bo'lardi (va R2'da yana bir fayl
turi paydo bo'lardi). Bu yerda rasm mazmun asosidagi kalit bilan keshga
yoziladi — mazmun o'zgarsa kalit ham o'zgaradi, ya'ni eskirish mumkin emas.
"""

import hashlib
import io

from django.core.cache import cache
from django.utils import timezone, translation
from django.utils.formats import date_format
from django.utils.translation import gettext
from PIL import Image, ImageDraw, ImageFilter

from .shriftlar import shrift

OLCHAM = (1200, 630)

# Keshda saqlash muddati. Havola bir marta Telegramga tashlangach, o'sha
# suhbatdagi qolgan mehmonlar Telegramning O'Z keshidan oladi — ya'ni bizga
# kelayotgan so'rovlar kam. Bir kun yetarli.
KESH_MUDDATI = 60 * 60 * 24


# --- Dizayn palitralari -----------------------------------------------
#
# Har bir dizayn shablonining o'z ranglari bor va ular shablon faylining
# boshidagi ":root" blokida ("--fon", "--asos", "--sarlavha", "--matn")
# turadi. Kartochka o'sha ranglarni takrorlaydi — shunda preview mehmon
# ochadigan sahifa bilan bir tilda gapiradi.
#
# NEGA NUSXA. Django shablonlarni faqat HTML sifatida chizadi; rang
# qiymatlarini undan Python tomonida o'qib olishning arzon yo'li yo'q.
# Ro'yxat qo'lda emas, shablon fayllaridan avtomatik o'qib olingan
# (aynan shu to'rt o'zgaruvchi grep qilingan). Yangi dizayn qo'shilganda
# yoki rang o'zgarganda shu yerga ham qo'shish kerak — aks holda dizayn
# STANDART (brend) palitrasi bilan chiziladi, ya'ni xato emas, shunchaki
# o'ziga xosligi yo'qoladi.
#
# Ro'yxatdagi to'rt eski dizayn (atlas, gulbarg, registon, sodda) ":root"
# ishlatmaydi — ular CSS o'zgaruvchilaridan oldin yozilgan. Ularning
# ranglari fayldagi eng ko'p uchraydigan qiymatlardan olingan.
PALITRA = {
    "adras": {"fon": "#f3f1e8", "asos": "#39699c", "sarlavha": "#2b5a8a", "matn": "#31445c"},
    "anor": {"fon": "#eef4ec", "asos": "#b3323b", "sarlavha": "#a8842c", "matn": "#3e4a3a"},
    "atlas": {"fon": "#f6f1e7", "asos": "#d1495b", "sarlavha": "#1f6f8b", "matn": "#33302a"},
    "aurora": {"fon": "#05060f", "asos": "#8b5cf6", "sarlavha": "#ffffff", "matn": "#e7e5f5"},
    "beshik": {"fon": "#f8f4ea", "asos": "#827343", "sarlavha": "#6a5c40", "matn": "#4c4639"},
    "chinni": {"fon": "#fdfdfa", "asos": "#1d4e89", "sarlavha": "#1d4e89", "matn": "#24354a"},
    "fotiha": {"fon": "#fbf1ee", "asos": "#bb4c5e", "sarlavha": "#a14f5d", "matn": "#4a2e30"},
    "gulbarg": {"fon": "#fdf6f0", "asos": "#b76e79", "sarlavha": "#7d4a50", "matn": "#4a3f35"},
    "kristall": {"fon": "#050510", "asos": "#a78bfa", "sarlavha": "#ffffff", "matn": "#ece9fa"},
    "kumush": {"fon": "#f5f4f1", "asos": "#8b8e96", "sarlavha": "#75787f", "matn": "#44464a"},
    "nahoroshi": {"fon": "#f8f0e2", "asos": "#a95e1b", "sarlavha": "#8a4a12", "matn": "#4a3520"},
    "nurafshon": {"fon": "#241a10", "asos": "#d9b45b", "sarlavha": "#f0d9a8", "matn": "#f0e6d4"},
    "qandil": {"fon": "#efe6d8", "asos": "#b3924a", "sarlavha": "#9c7c3c", "matn": "#4d4234"},
    "qirgiz": {"fon": "#9e111f", "asos": "#ffcc00", "sarlavha": "#ffe9a8", "matn": "#fff3e6"},
    "qizuzatish": {"fon": "#f7f1f5", "asos": "#88688d", "sarlavha": "#6b4f70", "matn": "#453040"},
    "qozoq": {"fon": "#eef6fb", "asos": "#0b86c8", "sarlavha": "#0b6aa9", "matn": "#123a56"},
    "ravoq": {"fon": "#efe9e2", "asos": "#a8842c", "sarlavha": "#8a6a1f", "matn": "#4a443c"},
    "registon": {"fon": "#0f2027", "asos": "#c9a227", "sarlavha": "#f2e3bb", "matn": "#e3ded2"},
    "sadaf": {"fon": "#f4f2ef", "asos": "#b39544", "sarlavha": "#8f7a3e", "matn": "#3d3a35"},
    "shoyi": {"fon": "#eef0f3", "asos": "#7590b5", "sarlavha": "#5a749b", "matn": "#3c4250"},
    "sodda": {"fon": "#fdfaf4", "asos": "#8a6d3b", "sarlavha": "#6f5730", "matn": "#2b2b2b"},
    "suzani": {"fon": "#f8f0e0", "asos": "#b3323b", "sarlavha": "#a12d33", "matn": "#43352a"},
    "tojik": {"fon": "#fffaf2", "asos": "#c22b33", "sarlavha": "#c22b33", "matn": "#3f3126"},
    "tugilgankun": {"fon": "#fbf1e6", "asos": "#b65728", "sarlavha": "#a84a1f", "matn": "#4a2f22"},
    "turkman": {"fon": "#6f1a1d", "asos": "#d9a960", "sarlavha": "#f0d9a8", "matn": "#f5e8d5"},
    "xatna": {"fon": "#f3f2e9", "asos": "#234b7a", "sarlavha": "#1f3a5f", "matn": "#22344a"},
    "yubiley": {"fon": "#f6f0f3", "asos": "#3f6b4e", "sarlavha": "#2c4a37", "matn": "#402e3d"},
    "zardoz": {"fon": "#21102e", "asos": "#d9b45b", "sarlavha": "#e9c268", "matn": "#f3e9d7"},
    "zarhal": {"fon": "#0b0b0d", "asos": "#d4af37", "sarlavha": "#f3e3b3", "matn": "#ece6d8"},
}

# Dizayn ro'yxatda topilmasa (yangi qo'shilgan, hali kiritilmagan) — saytning
# o'z brend ranglari: krem fon, oltin urg'u.
STANDART = {"fon": "#f6f0e2", "asos": "#a9812e", "sarlavha": "#17130f", "matn": "#4a4236"}


# --- Kichik yordamchilar ----------------------------------------------

def _rang(hex_qiymat, shaffoflik=1.0):
    h = hex_qiymat.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, int(round(255 * shaffoflik)))


def _yorugmi(hex_qiymat):
    """Fon och rangmi? Foto ustidagi parda va soyalar shunga qarab tanlanadi."""
    h = hex_qiymat.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    # Idrok etiladigan yorug'lik (ITU-R BT.601) — oddiy o'rtachadan aniqroq.
    return (0.299 * r + 0.587 * g + 0.114 * b) > 140


def _kenglik(shr, matn, oraliq=0):
    if not matn:
        return 0
    return sum(shr.getlength(ch) for ch in matn) + oraliq * (len(matn) - 1)


def _yoz(chiz, x, y, matn, shr, rang, oraliq=0):
    """Belgilar orasiga qo'shimcha bo'shliq (letter-spacing) bilan yozadi.

    Pillow'da bunday sozlama yo'q, shuning uchun har bir belgi alohida
    chiziladi. Yozuvlarning kattasi emas, faqat KICHIK bosh harfli
    yorliqlar shu yo'l bilan chiziladi — ular uchun kerning yo'qolishi
    sezilmaydi, siyraklik esa premium ko'rinish beradi.
    """
    if not oraliq:
        chiz.text((x, y), matn, font=shr, fill=rang, anchor="ls")
        return
    for ch in matn:
        chiz.text((x, y), ch, font=shr, fill=rang, anchor="ls")
        x += shr.getlength(ch) + oraliq


def _sigdir(shrift_nomi, matn, maks_kenglik, boshlangich, eng_kichik=34):
    """Matn berilgan kenglikka sig'adigan eng katta shrift o'lchamini topadi."""
    olcham = boshlangich
    while olcham > eng_kichik:
        shr = shrift(shrift_nomi, olcham)
        if shr.getlength(matn) <= maks_kenglik:
            return shr
        olcham -= 2
    return shrift(shrift_nomi, eng_kichik)


def _bolaklab(matn, shr, maks_kenglik, maks_qator=2):
    """Uzun matnni so'zlar bo'yicha qatorlarga ajratadi."""
    sozlar = matn.split()
    qatorlar, joriy = [], ""
    for soz in sozlar:
        sinov = f"{joriy} {soz}".strip()
        if shr.getlength(sinov) <= maks_kenglik or not joriy:
            joriy = sinov
        else:
            qatorlar.append(joriy)
            joriy = soz
        if len(qatorlar) == maks_qator - 1 and shr.getlength(joriy) > maks_kenglik:
            break
    if joriy:
        qatorlar.append(joriy)
    return qatorlar[:maks_qator]


# --- Fon ---------------------------------------------------------------

def _naqshli_fon(p):
    """Foto bo'lmaganda: dizayn foni + juda xira romb panjarasi.

    Naqsh ataylab deyarli ko'rinmas darajada (6%) — maqsadi e'tiborni
    tortish emas, tekis rangli to'rtburchakni "qog'oz"ga aylantirish.
    """
    tasvir = Image.new("RGB", OLCHAM, _rang(p["fon"])[:3])
    qatlam = Image.new("RGBA", OLCHAM, (0, 0, 0, 0))
    chiz = ImageDraw.Draw(qatlam)
    asos = _rang(p["asos"], 0.075)
    qadam, r = 74, 4
    qator = 0
    y = -qadam
    while y < OLCHAM[1] + qadam:
        surish = 0 if qator % 2 == 0 else qadam // 2
        x = -qadam + surish
        while x < OLCHAM[0] + qadam:
            chiz.polygon([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], fill=asos)
            x += qadam
        y += qadam // 2
        qator += 1
    tasvir = Image.alpha_composite(tasvir.convert("RGBA"), qatlam)

    # Markazga yumshoq yorug'lik — chekkalar biroz to'qroq bo'lib, matn
    # turadigan o'rta qism "ko'tarilib" turadi.
    #
    # TO'Q FONLI DIZAYNLARDA (zarhal, zardoz, aurora, kristall, nurafshon)
    # oq yorug'lik bilan bir xil kuch qo'yilsa, qora fon kulrangga aylanib
    # ketadi — aynan shu dizaynlarning butun ta'siri chuqur qorong'ilikda
    # bo'lgani uchun, bu ularni buzadi. Shu sabab to'q fonda yorug'lik
    # ancha kuchsiz va OQ emas, dizaynning o'z urg'u rangida beriladi
    # (oltin fonli nur — qorong'ilikni saqlaydi, ustiga issiqlik qo'shadi).
    yorug_fon = _yorugmi(p["fon"])
    vinyet = Image.new("L", OLCHAM, 0)
    ImageDraw.Draw(vinyet).ellipse(
        (-260, -400, OLCHAM[0] + 260, OLCHAM[1] + 400), fill=80 if yorug_fon else 22
    )
    vinyet = vinyet.filter(ImageFilter.GaussianBlur(120))
    nur = Image.new("RGBA", OLCHAM, (255, 255, 255, 255) if yorug_fon else _rang(p["asos"]))
    nur.putalpha(vinyet)
    return Image.alpha_composite(tasvir, nur)


def _fotoli_fon(fayl, p):
    """Mijozning fotosi fon sifatida: kesiladi, yumshatiladi, pardalanadi.

    Uch qadam ham zarur: (1) 1200x630 nisbatga KESISH — cho'zilgan foto
    darhol havaskor ko'rinadi; (2) YUMSHATISH — ustidagi yozuv tinch fonda
    o'qiladi; (3) dizayn rangidagi PARDA — kartochka o'sha dizayn oilasiga
    tegishli bo'lib qoladi va foto qanday bo'lishidan qat'i nazar matn
    kontrasti kafolatlanadi.
    """
    foto = Image.open(fayl)
    foto = foto.convert("RGB")

    nisbat = max(OLCHAM[0] / foto.width, OLCHAM[1] / foto.height)
    yangi = (max(1, round(foto.width * nisbat)), max(1, round(foto.height * nisbat)))
    foto = foto.resize(yangi, Image.LANCZOS)
    chap = (foto.width - OLCHAM[0]) // 2
    # Yuqoridan biroz yuqoriroq kesiladi: portret fotoda odamning yuzi
    # odatda markazdan tepada bo'ladi.
    tepa = max(0, (foto.height - OLCHAM[1]) // 3)
    foto = foto.crop((chap, tepa, chap + OLCHAM[0], tepa + OLCHAM[1]))
    foto = foto.filter(ImageFilter.GaussianBlur(3))

    # Parda ikki qatlamli: butun rasm ustidan YENGIL (fotoning o'zi
    # ko'rinib tursin — mehmon avvalo o'z tanishlarini ko'radi), matn
    # turadigan o'rta qismda esa QALIN. Bir tekis qalin parda qo'yilsa
    # foto shunchaki rangli tuman bo'lib qolardi; bir tekis yengil parda
    # esa fotoning yorug' joyiga tushgan yozuvni o'qib bo'lmas holga
    # keltirardi. Bu yerda ikkalasi ham hal bo'ladi.
    tasvir = Image.alpha_composite(foto.convert("RGBA"), Image.new("RGBA", OLCHAM, _rang(p["fon"], 0.40)))

    niqob = Image.new("L", OLCHAM, 0)
    ImageDraw.Draw(niqob).ellipse((-80, 96, OLCHAM[0] + 80, OLCHAM[1] - 46), fill=225)
    niqob = niqob.filter(ImageFilter.GaussianBlur(70))
    orta = Image.new("RGBA", OLCHAM, _rang(p["fon"]))
    orta.putalpha(niqob)
    return Image.alpha_composite(tasvir, orta)


# --- Bezaklar ----------------------------------------------------------

def _romka(chiz, p):
    """Tashqi romka va burchaklardagi ichki qavs belgilari.

    TAFTISH: birinchi variantda ikkita to'liq to'rtburchak chizilgan edi
    (tashqi va ichki) — natijada kartochka "jadval katagi"ga o'xshab qoldi
    va burchak bezaklari ichki to'rtburchak bilan qo'shilib, umuman
    ko'rinmay ketdi. Endi to'liq romka bitta, ichkarida esa faqat
    burchaklarda qisqa qavslar bor — bu bosma taklifnomalardagi klassik
    "passe-partout" usuli: ko'z burchaklarni ilg'aydi, o'rtasi esa
    bo'sh va tinch qoladi.
    """
    t = _rang(p["asos"], 0.55)
    qavs = _rang(p["asos"], 0.42)
    chiz.rectangle((38, 38, OLCHAM[0] - 39, OLCHAM[1] - 39), outline=t, width=2)

    ich, uzunlik = 18, 52
    for bx, by, ix, iy in (
        (38, 38, 1, 1),
        (OLCHAM[0] - 39, 38, -1, 1),
        (38, OLCHAM[1] - 39, 1, -1),
        (OLCHAM[0] - 39, OLCHAM[1] - 39, -1, -1),
    ):
        x, y = bx + ix * ich, by + iy * ich
        chiz.line((x, y, x + ix * uzunlik, y), fill=qavs, width=1)
        chiz.line((x, y, x, y + iy * uzunlik), fill=qavs, width=1)


def _ajratgich(chiz, y, markaz, p, kenglik=250):
    """Chiziq — romb — chiziq. Ismlar bilan sana orasidagi nafas.

    Sayt shablonlaridagi "--bezak-svg" bilan bir oilada: ikki yon chiziq va
    o'rtada to'rt qirrali belgi.
    """
    chiziq = _rang(p["asos"], 0.5)
    yarim = kenglik // 2
    chiz.line((markaz - yarim, y, markaz - 22, y), fill=chiziq, width=1)
    chiz.line((markaz + 22, y, markaz + yarim, y), fill=chiziq, width=1)
    r = 7
    chiz.polygon(
        [(markaz, y - r), (markaz + r, y), (markaz, y + r), (markaz - r, y)],
        fill=_rang(p["asos"], 0.9),
    )
    kr = 3
    chiz.polygon(
        [(markaz - 14, y - kr), (markaz - 14 + kr, y), (markaz - 14, y + kr), (markaz - 14 - kr, y)],
        fill=chiziq,
    )
    chiz.polygon(
        [(markaz + 14, y - kr), (markaz + 14 + kr, y), (markaz + 14, y + kr), (markaz + 14 - kr, y)],
        fill=chiziq,
    )


def _yonlama_chiziqli_yozuv(chiz, markaz, y, matn, shr, matn_rangi, chiziq_rangi, oraliq=5):
    """Ikki yonida ingichka chiziq bo'lgan kichik yozuv.

    Saytning yuqori panelidagi logotip aynan shu shaklda ("OQQUSHLAR",
    ostida chiziq-yozuv-chiziq) — reklama kartochkasi brendni o'sha
    tanish ko'rinishda takrorlaydi.
    """
    matn_kengligi = _kenglik(shr, matn, oraliq)
    _yoz(chiz, markaz - matn_kengligi / 2, y, matn, shr, matn_rangi, oraliq)
    chiziq_uzunligi = 96
    bosh = markaz - matn_kengligi / 2 - 22
    oxir = markaz + matn_kengligi / 2 + 22
    chiz.line((bosh - chiziq_uzunligi, y - 6, bosh, y - 6), fill=chiziq_rangi, width=1)
    chiz.line((oxir, y - 6, oxir + chiziq_uzunligi, y - 6), fill=chiziq_rangi, width=1)


def _reklama_chiz(til):
    """Faollashtirilmagan taklifnoma uchun kartochka — brend kartochkasi.

    NEGA ISMLAR YO'Q. To'lov tasdiqlanmagan taklifnomaning sahifasi
    begona odamga ismni ham, sanani ham ko'rsatmaydi (views.py'dagi
    "_taklifnoma_sahifasi" ichidagi izohga qarang) — o'sha ma'lumot
    kartochkada chiqib ketsa, himoyaning ma'nosi qolmasdi.

    NEGA BO'SH RASM EMAS. Bunday havola baribir kimgadir yuboriladi
    (mijoz o'zi sinab ko'radi, do'stiga tashlaydi). O'sha daqiqada
    Telegramda umumiy logotip emas, "bu taklifnoma hali faol emas"
    degan tushuntirish va saytning o'zi haqidagi qisqa ma'lumot
    ko'rinsa — chalkashlik ham yo'qoladi, biz uchun esa bu bepul
    reklama bo'ladi.
    """
    p = STANDART
    tasvir = _naqshli_fon(p)
    chiz = ImageDraw.Draw(tasvir)
    _romka(chiz, p)
    markaz = OLCHAM[0] // 2

    with translation.override(til or "uz"):
        # Ikkala matn ham loyihada allaqachon mavjud va yettala tilga
        # tarjima qilingan — shu sabab bu kartochka uchun bironta yangi
        # tarjima satri qo'shilmadi.
        yorliq = str(gettext("Taklifnoma hali faollashtirilmagan")).upper()
        shior = str(gettext("chiroyli raqamli taklifnomalar")).upper()

    yorliq_shr = shrift("manrope", 24)
    y_oraliq = 6
    while _kenglik(yorliq_shr, yorliq, y_oraliq) > OLCHAM[0] - 260 and y_oraliq > 2:
        y_oraliq -= 1
    y_kengligi = _kenglik(yorliq_shr, yorliq, y_oraliq)
    _yoz(chiz, markaz - y_kengligi / 2, 202, yorliq, yorliq_shr, _rang(p["matn"], 0.6), y_oraliq)

    nom_shr = shrift("cormorant", 92)
    nom = "OQQUSHLAR"
    nom_oraliq = 14
    nom_kengligi = _kenglik(nom_shr, nom, nom_oraliq)
    _yoz(chiz, markaz - nom_kengligi / 2, 364, nom, nom_shr, _rang(p["sarlavha"]), nom_oraliq)

    shior_shr = shrift("manrope", 20)
    s_oraliq = 5
    while _kenglik(shior_shr, shior, s_oraliq) > OLCHAM[0] - 460 and s_oraliq > 2:
        s_oraliq -= 1
    _yonlama_chiziqli_yozuv(chiz, markaz, 420, shior, shior_shr,
                            _rang(p["asos"], 0.95), _rang(p["asos"], 0.5), s_oraliq)

    brend_shr = shrift("manrope", 19)
    brend = "OQQUSHLAR.UZ"
    b_kengligi = _kenglik(brend_shr, brend, 5)
    _yoz(chiz, markaz - b_kengligi / 2, 556, brend, brend_shr, _rang(p["asos"], 0.6), 5)

    return tasvir.convert("RGB")


# --- Asosiy chizuvchi ---------------------------------------------------

def _ism_bolaklari(taklifnoma):
    """Kartochkadagi bosh yozuv — ISMLAR, bo'linadigan ko'rinishda.

    TAFTISH: avval bu yerda Taklifnoma.sarlavha ishlatilgan edi. Lekin u
    ba'zi marosimlarda marosim NOMINI ham o'z ichiga oladi ("Amir, Botir
    va Sardorlarning xatna to'ylari"), tepada esa yorliq sifatida yana
    "XATNA TO'YI" yozilardi — bitta kartochkada bir xil so'z ikki marta.
    "Boshqa" turida esa yorliq va sarlavha butunlay bir xil matn edi.
    Kartochkada vazifalar aniq bo'linadi: TEPADA marosim turi, O'RTADA
    faqat ismlar.

    Ajratuvchi ("&" yoki "·") alohida bo'lak sifatida qaytariladi —
    u ismlardan boshqa (urg'u) rangda chiziladi, bu bitta oddiy qatorni
    haqiqiy taklifnomaga o'xshatadigan eng arzon usul.
    """
    ismlar = [i.strip() for i in (taklifnoma.ism_1, taklifnoma.ism_2, taklifnoma.ism_3) if i and i.strip()]
    if not ismlar:
        return [(str(taklifnoma.sarlavha), False)]
    if len(ismlar) == 1:
        return [(ismlar[0], False)]
    ajratgich = "  &  " if len(ismlar) == 2 else "  ·  "
    bolaklar = []
    for i, ism in enumerate(ismlar):
        if i:
            bolaklar.append((ajratgich, True))
        bolaklar.append((ism, False))
    return bolaklar


def _matnlar(taklifnoma, til):
    """Kartochkaga tushadigan barcha yozuvlarni KERAKLI TILDA tayyorlaydi.

    Til so'rov bilan keladi (og:image manzilidagi "?t=" parametri), chunki
    ijtimoiy tarmoq roboti rasmni ALOHIDA so'rov bilan oladi — unda
    mehmonning sessiyasi ham, cookie'si ham bo'lmaydi.
    """
    with translation.override(til or "uz"):
        sana = timezone.localtime(taklifnoma.sana)
        return {
            "yorliq": str(taklifnoma.marosim_turi_matni).upper(),
            "bolaklar": _ism_bolaklari(taklifnoma),
            # "j E Y" — "d-F, Y" emas. "F" oyni bosh kelishikda beradi va
            # ruschada "12-Октябрь, 2026" degan g'aliz matn chiqadi; "E"
            # esa tilning o'z sana shakli ("12 октября 2026"), o'zbekcha
            # va boshqa tillarda farqi yo'q.
            "sana": date_format(sana, "j E Y"),
            "vaqt": date_format(sana, "H:i"),
            "joy": (taklifnoma.toyxona or "").strip(),
        }


def _chiz(taklifnoma, til, foto_fayl=None):
    p = PALITRA.get(getattr(taklifnoma.shablon, "kod", ""), STANDART)
    m = _matnlar(taklifnoma, til)

    tasvir = _fotoli_fon(foto_fayl, p) if foto_fayl is not None else _naqshli_fon(p)
    chiz = ImageDraw.Draw(tasvir)
    _romka(chiz, p)

    markaz = OLCHAM[0] // 2
    maks = OLCHAM[0] - 260

    # --- Marosim yorlig'i (eng tepada, siyrak bosh harflar) ---
    yorliq_shr = shrift("manrope", 25)
    yorliq = m["yorliq"]
    oraliq = 7
    while _kenglik(yorliq_shr, yorliq, oraliq) > maks and oraliq > 2:
        oraliq -= 1
    y_kengligi = _kenglik(yorliq_shr, yorliq, oraliq)
    _yoz(chiz, markaz - y_kengligi / 2, 160, yorliq, yorliq_shr, _rang(p["asos"], 0.95), oraliq)

    # --- Ismlar ---
    bolaklar = m["bolaklar"]
    tolik = "".join(b[0] for b in bolaklar)
    sarlavha_shr = _sigdir("cormorant", tolik, maks, 104, 46)
    if sarlavha_shr.getlength(tolik) <= maks:
        jami = sum(sarlavha_shr.getlength(b[0]) for b in bolaklar)
        x = markaz - jami / 2
        for matn, urgu in bolaklar:
            rang = _rang(p["asos"], 0.85) if urgu else _rang(p["sarlavha"])
            chiz.text((x, 300), matn, font=sarlavha_shr, fill=rang, anchor="ls")
            x += sarlavha_shr.getlength(matn)
    else:
        # Juda uzun ism(lar) — eng kichik o'lchamda ham sig'madi. Bunda
        # rangli ajratgichdan voz kechiladi va matn ikki qatorga bo'linadi:
        # o'qilishi bezakdan muhimroq.
        kichik = shrift("cormorant", 62)
        qatorlar = _bolaklab(tolik, kichik, maks, 2)
        for i, qator in enumerate(qatorlar):
            chiz.text((markaz, 272 + i * 66), qator, font=kichik,
                      fill=_rang(p["sarlavha"]), anchor="ms")

    # --- Ajratgich ---
    _ajratgich(chiz, 358, markaz, p)

    # --- Sana va vaqt ---
    sana_matni = f"{m['sana']}  ·  {m['vaqt']}"
    sana_shr = _sigdir("manrope", sana_matni, maks, 34, 22)
    s_kengligi = _kenglik(sana_shr, sana_matni, 3)
    _yoz(chiz, markaz - s_kengligi / 2, 418, sana_matni, sana_shr, _rang(p["matn"], 0.92), 3)

    # --- To'yxona (bo'lsa) ---
    if m["joy"]:
        joy_shr = _sigdir("manrope", m["joy"], maks, 25, 18)
        j_kengligi = _kenglik(joy_shr, m["joy"], 2)
        _yoz(chiz, markaz - j_kengligi / 2, 462, m["joy"], joy_shr, _rang(p["matn"], 0.62), 2)

    # --- Brend (eng pastda, jim) ---
    brend_shr = shrift("manrope", 19)
    brend = "OQQUSHLAR.UZ"
    b_kengligi = _kenglik(brend_shr, brend, 5)
    _yoz(chiz, markaz - b_kengligi / 2, 556, brend, brend_shr, _rang(p["asos"], 0.6), 5)

    return tasvir.convert("RGB")


def _foto_fayli(taklifnoma):
    """Mijoz yuklagan birinchi fotoni qaytaradi (bo'lmasa None).

    ".path" ATAYLAB ishlatilmaydi: production'da fayllar S3-mos xotirada
    (Cloudflare R2) turadi va u yerda lokal yo'l umuman mavjud emas —
    ".open()" esa ikkala holatda ham ishlaydi.
    """
    if not taklifnoma.pk:
        return None
    yozuv = taklifnoma.rasmlar.first()
    if not yozuv or not yozuv.rasm:
        return None
    try:
        with yozuv.rasm.open("rb") as f:
            return io.BytesIO(f.read())
    except Exception:
        # Fayl o'chirilgan yoki xotira javob bermadi — kartochka fotosiz
        # ham to'liq ishlaydi, shuning uchun bu xato sahifani buzmasligi kerak.
        return None


def kesh_kaliti(taklifnoma, til):
    """Kartochka MAZMUNIDAN kelib chiqadigan kalit.

    Ismlar, sana yoki dizayn o'zgarsa kalit ham o'zgaradi — ya'ni eskirgan
    rasm qaytishi mumkin emas va hech qayerda "keshni tozalash" kerak emas.
    """
    xom = "|".join([
        taklifnoma.slug,
        til or "uz",
        taklifnoma.sarlavha,
        str(taklifnoma.sana),
        str(getattr(taklifnoma.shablon, "kod", "")),
        taklifnoma.marosim_turi,
        taklifnoma.boshqa_tadbir_nomi or "",
        taklifnoma.toyxona or "",
        str(getattr(taklifnoma.rasmlar.first(), "pk", "") if taklifnoma.pk else ""),
    ])
    return "ulashish:" + hashlib.md5(xom.encode("utf-8")).hexdigest()


def _baytlar(tasvir):
    xotira = io.BytesIO()
    # PNG emas, JPEG: kartochkada fotosurat va yumshoq gradientlar bor,
    # bunday tasvirda JPEG bir necha barobar kichik chiqadi (Telegram
    # preview'ni tezroq oladi), sifat farqi esa ko'rinmaydi.
    tasvir.save(xotira, "JPEG", quality=88, optimize=True, progressive=True)
    return xotira.getvalue()


def kartochka(taklifnoma, til="uz"):
    """Taklifnoma kartochkasining JPEG baytlari (keshdan yoki yangi chizib)."""
    kalit = kesh_kaliti(taklifnoma, til)
    tayyor = cache.get(kalit)
    if tayyor:
        return tayyor
    baytlar = _baytlar(_chiz(taklifnoma, til, _foto_fayli(taklifnoma)))
    cache.set(kalit, baytlar, KESH_MUDDATI)
    return baytlar


def reklama_kartochkasi(til="uz"):
    """Faollashtirilmagan taklifnoma uchun brend kartochkasining baytlari.

    Bu rasm barcha shunday havolalar uchun BIR XIL — ya'ni tilga bitta
    kesh yozuvi yetarli va u amalda doim keshdan chiqadi.
    """
    kalit = f"ulashish:reklama:{til or 'uz'}"
    tayyor = cache.get(kalit)
    if tayyor:
        return tayyor
    baytlar = _baytlar(_reklama_chiz(til))
    cache.set(kalit, baytlar, KESH_MUDDATI)
    return baytlar
