# -*- coding: utf-8 -*-
"""Shablonlardagi {% static %} havolalarini tekshiradi.

NEGA KERAK. Loyihada statik fayllar "manifest" rejimida ishlaydi
(CompressedManifestStaticFilesStorage). Bu rejimda mavjud bo'lmagan
faylga murojaat qilinsa, Django ValueError tashlaydi va sahifa 500
bo'ladi — LEKIN faqat production'da (DEBUG=False). Lokalda, DEBUG=True
bilan, xuddi shu havola hech qanday xatosiz ishlayveradi.

Aynan shu farq tufayli admin panelida bir marta o'lik havola qolib
ketgan ("taklif/logo-belgi.png" — logotip qayta ishlanganda fayl
o'chirilgan, havola qolgan) va u butun admin panelni yiqitgan. Sayt
sahifalari ishlab turgani uchun muammo uzoq vaqt sezilmagan.

Ishlatish (deploydan OLDIN):

    python manage.py statik_tekshir

Hech narsa topilmasa — 0 qaytaradi. O'lik havola topilsa, ro'yxatini
chiqarib, 1 qaytaradi (CI/skriptda ishlatish uchun).
"""
import os
import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand

# {% static 'yol' %} yoki {% static "yol" %} — faqat QAT'IY (o'zgaruvchisiz)
# yo'llar. O'zgaruvchili chaqiruvlar ({% static rasm.url %}) tekshirilmaydi,
# chunki ularning qiymati faqat ish paytida ma'lum bo'ladi.
STATIC_QOLIP = re.compile(r"""\{%\s*static\s+(['"])([^'"]+)\1\s*%\}""")


class Command(BaseCommand):
    help = "Shablonlardagi {% static %} havolalari haqiqatan mavjudligini tekshiradi"

    def handle(self, *args, **sozlamalar):
        papkalar = []
        for konfig in settings.TEMPLATES:
            papkalar.extend(str(y) for y in konfig.get("DIRS", []))
        # Ilova ichidagi templates/ papkalari
        for ilova_yoli in (settings.BASE_DIR,):
            for ildiz, _, _ in os.walk(ilova_yoli):
                if os.path.basename(ildiz) == "templates" and "venv" not in ildiz:
                    papkalar.append(ildiz)

        korilgan = set()
        topilmadi = []
        jami_havola = 0

        for papka in papkalar:
            for ildiz, _, fayllar in os.walk(papka):
                for f in fayllar:
                    if not f.endswith((".html", ".svg", ".txt")):
                        continue
                    yol = os.path.join(ildiz, f)
                    if yol in korilgan:
                        continue
                    korilgan.add(yol)
                    try:
                        matn = open(yol, encoding="utf-8").read()
                    except (OSError, UnicodeDecodeError):
                        continue
                    for _, havola in STATIC_QOLIP.findall(matn):
                        jami_havola += 1
                        if finders.find(havola) is None:
                            topilmadi.append((os.path.relpath(yol, str(settings.BASE_DIR)), havola))

        self.stdout.write(
            f"Tekshirildi: {len(korilgan)} ta shablon, {jami_havola} ta static havola."
        )
        if not topilmadi:
            self.stdout.write(self.style.SUCCESS("Barcha havolalar joyida."))
            return

        self.stdout.write(self.style.ERROR(f"\nO'LIK HAVOLA: {len(topilmadi)} ta"))
        for shablon, havola in topilmadi:
            self.stdout.write(f"  {shablon}\n      -> {havola}")
        self.stdout.write(
            self.style.WARNING(
                "\nBular production'da (DEBUG=False) o'sha sahifani 500 qiladi."
            )
        )
        raise SystemExit(1)
