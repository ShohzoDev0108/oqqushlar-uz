# -*- coding: utf-8 -*-
"""Yuklangan rasmlarni saqlashdan oldin optimallashtirish.

TAFTISH TOPILMASI. Rasm mijoz yuklagan holida, hech qanday ishlovsiz
saqlanardi. Bu uch xil muammo tug'dirardi.

1. OG'IRLIK. Zamonaviy telefon fotosi 4000x3000 piksel va 6-8 MB
   bo'ladi. Taklifnomada ikkitagacha rasm bor, ya'ni har bir mehmon
   sahifani ochganda 16 MB gacha yuklab olardi. To'y taklifnomasini
   esa yuzlab mehmon, ko'pincha mobil internetdan ochadi. Bu ham
   sekinlik, ham mehmonning trafigi, ham R2 hisobidagi pul.

2. EXIF BURCHAGI. Telefon rasmni ko'pincha yon holatda saqlab, "aslida
   90 gradus burilgan" degan belgini EXIF ichiga yozadi. Ba'zi brauzer
   bu belgini o'qiydi, ba'zisi yo'q — natijada kelin-kuyovning fotosi
   qayrilib ko'rinishi mumkin edi.

3. EXIF MAXFIYLIGI — eng jiddiysi. Telefon fotosi ichida GPS
   KOORDINATASI bo'ladi. Taklifnoma sahifasi esa havolani bilgan
   HAR KIMGA ochiq. Ya'ni mijozning uyida olingan fotosi bilan birga
   uning uy manzili ham ommaga chiqib ketardi. Bu yerda rasm qaytadan
   yozilgani uchun barcha metama'lumot — GPS ham, qurilma nomi ham,
   sana ham — butunlay tushib qoladi.

QAROR: WebP. Bir xil ko'rinish uchun JPEG'dan sezilarli kichik, va
2026-yilda barcha zamonaviy brauzerlar qo'llab-quvvatlaydi.
"""
import io
import logging
import os

from django.core.files.base import ContentFile

jurnal = logging.getLogger("taklif.rasm")

# Uzun tomon bo'yicha eng katta o'lcham.
#
# Taklifnomada rasm ekran kengligida ko'rsatiladi. 1600 piksel — hatto
# Retina ekranli telefonda ham yetarli; undan kattasi ko'zga bilinmaydi,
# lekin faylni ikki-uch barobar og'irlashtiradi.
MAKS_TOMON = 1600

# WebP sifati. 82 — ko'z ilg'amaydigan yo'qotish bilan sezilarli yutuq.
SIFAT = 82

# Namuna rasmlar yaratish formasida bir vaqtning o'zida bir nechtasi
# ko'rsatiladi, ya'ni ular yig'ilib og'irlik qiladi — biroz kichikroq.
NAMUNA_MAKS_TOMON = 1200

# TAFTISH TOPILMASI (2026-09-14): eng katta ruxsat etilgan piksel soni
# (kenglik x balandlik). Bu "dekompressiya bombasi" turidagi buzuq
# fayllardan himoya qiladi — masalan bir necha kilobaytli, lekin sarlavhasida
# o'n minglab x o'n minglab piksel deb yozilgan PNG/rasm, uni to'liq
# dekodlashga urinish xotirani (va CPU'ni) bir zumda tugatib qo'yishi
# mumkin. Tekshiruv `Image.open()`dan KEYIN, lekin piksel MA'LUMOTINI
# o'qishdan (masalan exif_transpose/thumbnail) OLDIN bajariladi — chunki
# `Image.open()` faylning faqat sarlavhasini o'qiydi, haqiqiy dekodlash
# birinchi piksel-darajasidagi amalda boshlanadi.
#
# 40 million piksel — hatto eng yangi flagman telefonlarning eng katta
# fotosidan (odatda 12-50 MP) ham keng chegara bilan katta, shuning
# uchun haqiqiy mijoz fotosi bu yerda hech qachon rad etilmaydi.
MAKS_PIKSEL = 40_000_000


class RasmXatosi(Exception):
    """Rasmni xavfsiz optimallashtirib bo'lmadi.

    TAFTISH TOPILMASI (2026-09-14): ilgari optimallashtirish
    muvaffaqiyatsiz bo'lganda chaqiruvchi (models.py'dagi
    "_rasmni_optimallashtirib_saqlash") ASL — siqilmagan, EXIF/GPS
    metama'lumoti hali o'chirilmagan — faylni o'zgarishsiz saqlab
    qo'yardi. Bu modul boshidagi izohda aytilgan ikkala asosiy maqsadni
    ham (og'irlikni kamaytirish VA GPS/metama'lumotni tozalash)
    yo'qqa chiqarardi — aynan xato/buzuq holatlarda, ya'ni himoya eng
    kerak bo'lgan paytda. Endi bunday holatda fayl umuman SAQLANMAYDI —
    shu xato ko'tariladi, chaqiruvchi tomon buni ushlab, mijozga
    tushunarli xabar ko'rsatishi yoki so'rovni rad etishi kerak.
    """


def optimallashtir(fayl, maks_tomon=MAKS_TOMON, sifat=SIFAT):
    """Rasmni WebP'ga o'giradi, kichraytiradi va metama'lumotini tashlaydi.

    Qaytaradi: yangi ContentFile, yoki ishlov bermay bo'lmasa — None.

    TAFTISH TOPILMASI (2026-09-14): bu funksiyaning o'zi hech qachon
    istisno (exception) ko'tarmaydi — ichkarida yuz bergan xato shu
    yerda "yutib yuboriladi" va faqat None qaytariladi. Bu ATAYLAB: bir
    dona buzuq/g'alati fayl butun so'rovni 500-xato bilan qulatmasligi
    kerak. LEKIN None qaytganda asl faylni o'zgarishsiz saqlab qolish —
    bu funksiyaning ISHI EMAS: qaytadan qarang RasmXatosi izohiga
    ("_rasmni_optimallashtirib_saqlash" — models.py) — ASL fayl endi
    hech qachon saqlanmaydi, shu javobgarlik chaqiruvchida.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:  # pragma: no cover
        jurnal.error("Pillow o'rnatilmagan — rasm optimallashtirilmadi")
        return None

    try:
        fayl.seek(0)
        rasm = Image.open(fayl)

        # Piksel-bombasi tekshiruvi — modul boshidagi MAKS_PIKSEL izohiga
        # qarang. `rasm.size` faqat sarlavhadan o'qiladi, hali to'liq
        # dekodlashga OLIB KELMAYDI — shuning uchun bu tekshiruv buzuq
        # fayl uchun ham xavfsiz va arzon.
        kenglik, balandlik = rasm.size
        if kenglik * balandlik > MAKS_PIKSEL:
            jurnal.warning(
                "Rasm juda katta (%sx%s = %s piksel, chegara %s) — "
                "optimallashtirilmadi",
                kenglik, balandlik, kenglik * balandlik, MAKS_PIKSEL,
            )
            return None

        # JPEG uchun tezlashtirilgan dekodlash: libjpeg faylni to'liq
        # o'lchamda dekodlab, KEYIN kichraytirish o'rniga, DCT darajasida
        # to'g'ridan-to'g'ri kerakli o'lchamga YAQIN holda o'qiydi — katta
        # telefon fotolarida dekodlash vaqti va xotira sarfini sezilarli
        # kamaytiradi. Boshqa formatlar uchun Pillow bu chaqiruvni
        # jimgina e'tiborsiz qoldiradi (faqat JPEG/MPO'da ishlaydi), va
        # u albatta piksel ma'lumotini o'qishdan (masalan quyidagi
        # exif_transpose) OLDIN chaqirilishi kerak.
        rasm.draft("RGB", (maks_tomon, maks_tomon))

        # EXIF'dagi burilish belgisini HAQIQIY burilishga aylantiradi.
        # Shundan keyin belgining o'zi keraksiz bo'ladi.
        rasm = ImageOps.exif_transpose(rasm)

        # Shaffoflikni saqlaymiz (masalan PNG logotip), qolganini RGB.
        shaffof = rasm.mode in ("RGBA", "LA") or (
            rasm.mode == "P" and "transparency" in rasm.info
        )
        rasm = rasm.convert("RGBA" if shaffof else "RGB")

        # thumbnail() nisbatni saqlaydi va rasm allaqachon kichik bo'lsa
        # uni KATTALASHTIRMAYDI — bizga aynan shu kerak.
        rasm.thumbnail((maks_tomon, maks_tomon), Image.LANCZOS)

        buffer = io.BytesIO()
        # Pillow metama'lumotni o'zi ko'chirmaydi — ya'ni GPS, qurilma
        # nomi va sana shu yerda tushib qoladi. Bu qo'shimcha emas,
        # ASOSIY maqsadlardan biri (modul boshidagi 3-band).
        rasm.save(buffer, format="WEBP", quality=sifat, method=6)
        baytlar = buffer.getvalue()
    except Exception as xato:
        jurnal.warning("Rasmni optimallashtirib bo'lmadi: %s", xato)
        return None

    if not baytlar:
        return None

    asos = os.path.splitext(os.path.basename(getattr(fayl, "name", "rasm")))[0]
    # Nom bo'sh yoki faqat nuqtalardan iborat bo'lib qolmasin.
    asos = asos.strip(". ") or "rasm"
    return ContentFile(baytlar, name=f"{asos}.webp")
