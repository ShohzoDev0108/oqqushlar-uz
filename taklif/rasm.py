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


def optimallashtir(fayl, maks_tomon=MAKS_TOMON, sifat=SIFAT):
    """Rasmni WebP'ga o'giradi, kichraytiradi va metama'lumotini tashlaydi.

    Qaytaradi: yangi ContentFile, yoki ishlov bermay bo'lmasa — None
    (chaqiruvchi bunday holda asl faylni o'zgarishsiz saqlaydi).

    Xato yutib yuborilishi ATAYLAB: rasm optimallashmasa ham mijozning
    taklifnomasi yaratilishi kerak. Buzuq fayl uchun butun so'rovni
    qulatish mutlaqo nomutanosib javob bo'lardi.
    """
    try:
        from PIL import Image, ImageOps
    except ImportError:  # pragma: no cover
        jurnal.error("Pillow o'rnatilmagan — rasm optimallashtirilmadi")
        return None

    try:
        fayl.seek(0)
        rasm = Image.open(fayl)

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
