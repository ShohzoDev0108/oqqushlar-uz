# -*- coding: utf-8 -*-
"""Serverda rasm chizish uchun brend shriftlari.

Saytning o'zi shriftlarni Google Fonts'dan brauzerga yuklaydi. Lekin
ulashish kartochkasi SERVERDA chiziladi va Pillow'ga shrift FAYLI kerak —
tizimda esa (Debian konteynerida) na Cormorant, na Manrope bor, ya'ni
mavjud bo'lgan birinchi shrift bilan chizilsa kartochka boshqa sayt kabi
ko'rinardi.

Shu sabab ikkala shriftning kerakli og'irliklari repozitoriyga qo'shildi.
Fayllar Google Fonts'ning o'zgaruvchan (variable) versiyasidan olingan:
kerakli og'irlik ajratib olindi (fontTools.varLib.instancer) va faqat
Lotin + Kirill belgilar qoldirildi (fontTools.subset) — shuning uchun
ikkalasi birgalikda ~255 KB, asl fayllar esa 1.4 MB edi. Qayta yasash
kerak bo'lsa: static/taklif/shriftlar/YASASH.py. Ikkala shrift ham SIL
Open Font License bilan tarqatiladi, litsenziya matni o'sha papkada.
"""

import os

from PIL import ImageFont

KATALOG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "static", "taklif", "shriftlar")

FAYLLAR = {
    # Ismlar uchun — saytdagi sarlavhalar bilan bir xil serif.
    "cormorant": "CormorantGaramond-SemiBold.ttf",
    # Yorliq, sana, brend qatori uchun.
    "manrope": "Manrope-Medium.ttf",
}

# Bir xil o'lchamdagi shrift qayta-qayta ochilmasin: ImageFont.truetype
# har chaqiruvda faylni o'qiydi va FreeType obyektini quradi, kartochkada
# esa bitta shrift bir necha marta kerak bo'ladi.
_ombor = {}


def shrift(nom, olcham):
    kalit = (nom, int(olcham))
    if kalit not in _ombor:
        _ombor[kalit] = ImageFont.truetype(os.path.join(KATALOG, FAYLLAR[nom]), int(olcham))
    return _ombor[kalit]
