# -*- coding: utf-8 -*-
"""Shablon CSS'ining takrorlanmasligini qo'riqlaydigan testlar.

NEGA KERAK. Parda CSS'i 20 ta shablon faylida so'zma-so'z takrorlanardi
(2400 qatordan ortiq). U umumiy faylga chiqarildi. Bu testlar shu
holatning saqlanishini ta'minlaydi: kimdir yangi shablon yasab, parda
CSS'ini yana nusxa ko'chirib qo'ysa — test darrov aytadi.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

PAPKA = Path(settings.BASE_DIR) / "taklif" / "templates" / "taklif" / "shablonlar"
UMUMIY = 'taklif/shablonlar/_uslub_parda.html'
# Parda CSS'ining faqat shu blokda uchraydigan, aniq belgisi
BELGI = ".parda-yurak-wrap"


def dizayn_fayllari():
    return sorted(f for f in PAPKA.glob("*.html") if not f.name.startswith("_"))


class PardaUslubiTest(TestCase):
    def test_umumiy_fayl_mavjud_va_bosh_emas(self):
        fayl = PAPKA / "_uslub_parda.html"
        self.assertTrue(fayl.exists(), "_uslub_parda.html topilmadi")
        self.assertIn(BELGI, fayl.read_text(encoding="utf-8"))

    def test_hech_bir_shablon_parda_cssini_takrorlamaydi(self):
        aybdorlar = []
        for fayl in dizayn_fayllari():
            matn = fayl.read_text(encoding="utf-8")
            # izohlarni hisobga olmaymiz — gap KODDA
            kod = re.sub(r"/\*.*?\*/", "", matn, flags=re.S)
            if BELGI in kod and UMUMIY not in matn:
                aybdorlar.append(fayl.name)
        self.assertEqual(
            aybdorlar, [],
            "bu shablonlar parda CSS'ini o'zida saqlab qolgan — "
            f'o\'rniga "{UMUMIY}" include qilinishi kerak: {aybdorlar}',
        )

    def test_include_root_blokidan_keyin_turadi(self):
        """CSS kaskadi tartibga bog'liq: umumiy uslub ":root" o'zgaruvchilari
        e'lon qilingandan KEYIN kelishi shart, aks holda u o'zgaruvchilarni
        ko'rmaydi."""
        for fayl in dizayn_fayllari():
            matn = fayl.read_text(encoding="utf-8")
            if UMUMIY not in matn:
                continue
            with self.subTest(shablon=fayl.name):
                self.assertLess(
                    matn.index(":root {"), matn.index(UMUMIY),
                    f"{fayl.name}: include ':root' dan oldin turibdi",
                )
