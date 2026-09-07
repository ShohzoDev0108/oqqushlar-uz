# -*- coding: utf-8 -*-
"""Shu papkadagi .ttf fayllarni QAYTA yasash uchun skript.

Odatda ishga tushirish SHART EMAS — tayyor fayllar repozitoriyda turadi.
Kerak bo'ladigan payt: shrift versiyasi yangilanganda yoki kartochkaga
yangi belgilar (masalan boshqa alifbo) kerak bo'lganda.

Ishga tushirish:

    pip install fonttools brotli
    curl -Lo /tmp/CormorantGaramond.ttf \
      "https://github.com/google/fonts/raw/main/ofl/cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf"
    curl -Lo /tmp/Manrope.ttf \
      "https://github.com/google/fonts/raw/main/ofl/manrope/Manrope%5Bwght%5D.ttf"
    python YASASH.py

Ikki qadam bajariladi:
  1) O'ZGARUVCHAN shriftdan bitta qat'iy og'irlik ajratiladi (Pillow
     o'zgaruvchan o'qni o'zi sozlay olmaydi);
  2) faqat kerakli belgilar qoldiriladi — Lotin va Kirill (mijoz ismi
     har ikkisida ham bo'lishi mumkin) hamda tinish belgilari. Shusiz
     Cormorant fayli 1.2 MB bo'lardi.
"""
import subprocess
import sys

# Lotin + diakritika + Kirill (o'zbek, rus, qozoq, qirg'iz, tojik,
# turkman, qoraqalpoq harflari shu oraliqlarda) + tinish/valyuta belgilari.
UNICODES = ("U+0020-024F,U+02B0-02FF,U+0300-036F,U+0400-04FF,"
            "U+2000-206F,U+20B8-20BF,U+2122,U+2190-2193,U+25CA,U+2660-2667")

ISHLAR = [
    ("/tmp/CormorantGaramond.ttf", 600, "CormorantGaramond-SemiBold.ttf"),
    ("/tmp/Manrope.ttf", 500, "Manrope-Medium.ttf"),
]

if __name__ == "__main__":
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    for manba, ogirlik, nom in ISHLAR:
        f = TTFont(manba)
        instancer.instantiateVariableFont(f, {"wght": ogirlik}, inplace=True,
                                          updateFontNames=True)
        oraliq = "/tmp/_oraliq.ttf"
        f.save(oraliq)
        subprocess.run([sys.executable, "-m", "fontTools.subset", oraliq,
                        f"--unicodes={UNICODES}",
                        "--layout-features=kern,liga,ccmp,locl,mark,mkmk",
                        "--no-hinting", f"--output-file={nom}"], check=True)
        print("tayyor:", nom)
