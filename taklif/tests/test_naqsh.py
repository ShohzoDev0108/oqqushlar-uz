# -*- coding: utf-8 -*-
"""Fon naqshi: qaysi naqsh chiqishi va u qanday chizilishi.

Bu yerdagi asosiy xavf — naqsh qo'shilishi bilan MAVJUD taklifnomalar
ko'rinishining o'zgarib ketishi. Shuning uchun birinchi test aynan
shuni tekshiradi: naqsh belgilanmagan taklifnomada sahifaga hech
qanday qatlam qo'shilmasligi kerak.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from taklif.models import Naqsh, Taklifnoma

from .yordamchi import shablon_yarat


# DIQQAT: kalit HAQIQIY fayl nomi bo'lishi shart. Sayt
# ManifestStaticFilesStorage ishlatadi — u "{% static %}" da mavjud
# bo'lmagan faylni ko'rsa xato ko'taradi, ya'ni o'ylab topilgan
# "sinov-naqsh" bilan sahifa umuman render bo'lmaydi.
def naqsh_yarat(kalit="sozana-gul", **qoshimcha):
    maydonlar = {"nomi": "Sinov naqshi", "kalit": kalit}
    maydonlar.update(qoshimcha)
    return Naqsh.objects.create(**maydonlar)


def taklifnoma_yarat(shablon, **qoshimcha):
    maydonlar = {
        "ism_1": "Sardor",
        "slug": "sardor-sinov",
        "shablon": shablon,
        "sana": timezone.now() + timedelta(days=30),
        "faol": True,
        "tolangan": True,
    }
    maydonlar.update(qoshimcha)
    return Taklifnoma.objects.create(**maydonlar)


class NaqshTanlashTest(TestCase):
    """Qaysi naqsh ishlatiladi: taklifnomaniki, shablonniki yoki hech qaysi."""

    def setUp(self):
        self.shablon = shablon_yarat()

    def _sahifa(self, taklifnoma):
        javob = self.client.get(f"/{taklifnoma.slug}/")
        self.assertEqual(javob.status_code, 200)
        return javob.content.decode()

    def test_naqsh_belgilanmagan_bolsa_qatlam_umuman_chiqmaydi(self):
        """Eng muhim test: eski taklifnomalar o'zgarmasligi kerak."""
        t = taklifnoma_yarat(self.shablon)
        self.assertNotIn("oq-naqsh", self._sahifa(t))

    def test_shablonning_asosiy_naqshi_ishlatiladi(self):
        n = naqsh_yarat()
        self.shablon.asosiy_naqsh = n
        self.shablon.save()
        t = taklifnoma_yarat(self.shablon)
        sahifa = self._sahifa(t)
        self.assertIn("oq-naqsh", sahifa)
        self.assertIn("sozana-gul", sahifa)

    def test_taklifnomaning_ozi_shablonnikidan_ustun(self):
        asosiy = naqsh_yarat()
        tanlangan = naqsh_yarat(kalit="kigiz-romb", nomi="Kigiz")
        self.shablon.asosiy_naqsh = asosiy
        self.shablon.save()
        t = taklifnoma_yarat(self.shablon, naqsh=tanlangan)
        sahifa = self._sahifa(t)
        self.assertIn("kigiz-romb", sahifa)
        self.assertNotIn("sozana-gul", sahifa)


    def test_qatlam_sahifaning_eng_tepasida_turadi(self):
        """Regressiya: qatlam ".ichki" (position: relative) ichida bo'lsa,
        "top: 0" sahifa boshini emas, o'sha blokning boshini bildiradi va
        naqsh hero'dan pastga tushib qolardi. Shuning uchun u <body> ning
        bevosita bolasi bo'lishi shart. Jonli saytda topilgan."""
        n = naqsh_yarat(joylashuv="tepa")
        self.shablon.asosiy_naqsh = n
        self.shablon.save()
        t = taklifnoma_yarat(self.shablon)
        sahifa = self._sahifa(t)
        tana = sahifa.index("<body>")
        qatlam = sahifa.index('class="oq-naqsh"')
        oram = sahifa.index('<div class="wrapper">')
        self.assertLess(tana, qatlam, "qatlam <body> dan keyin turishi kerak")
        self.assertLess(qatlam, oram, "qatlam .wrapper dan OLDIN turishi kerak")

class NaqshChizilishiTest(TestCase):
    """Ikki joylashuv har xil CSS beradi."""

    def setUp(self):
        self.shablon = shablon_yarat()

    def _sahifa(self, naqsh):
        self.shablon.asosiy_naqsh = naqsh
        self.shablon.save()
        t = taklifnoma_yarat(self.shablon)
        javob = self.client.get(f"/{t.slug}/")
        self.assertEqual(javob.status_code, 200)
        return javob.content.decode()

    def test_tepa_takrorlanmaydi(self):
        sahifa = self._sahifa(naqsh_yarat(joylashuv="tepa"))
        self.assertIn("mask-repeat: no-repeat", sahifa)
        self.assertIn("position: absolute", sahifa)

    def test_maydon_plita_olchamini_ishlatadi(self):
        sahifa = self._sahifa(
            naqsh_yarat(kalit="sozana-novda", joylashuv="maydon", olcham=240)
        )
        self.assertIn("mask-size: 240px auto", sahifa)
        self.assertIn("position: fixed", sahifa)

    def test_shaffoflik_sahifaga_tushadi(self):
        sahifa = self._sahifa(naqsh_yarat(shaffoflik=Decimal("0.22")))
        self.assertIn("opacity: 0.22", sahifa)

    def test_ozbek_tilida_ham_nuqtali_kasr_chiqadi(self):
        """Regressiya: o'zbek tilida Django kasrni vergul bilan yozardi
        ("0,30"), CSS esa qoidani tashlab yuborib naqshni to'liq
        ko'rinadigan qilib qo'yardi. Jonli saytda topilgan."""
        from django.utils import translation

        with translation.override("uz"):
            sahifa = self._sahifa(
                naqsh_yarat(kalit="sozana-novda", shaffoflik=Decimal("0.30"),
                            olcham=250, joylashuv="maydon")
            )
        self.assertIn("opacity: 0.30", sahifa)
        self.assertNotIn("0,30", sahifa)
        self.assertIn("mask-size: 250px auto", sahifa)

    def test_rang_shablondan_olinadi(self):
        """Naqsh o'z rangini olib kelmaydi — rang CSS o'zgaruvchisidan."""
        sahifa = self._sahifa(naqsh_yarat())
        self.assertIn("var(--naqsh-rang, var(--asos))", sahifa)


class NaqshFayliTest(TestCase):
    def test_fayl_yoli_kalitdan_quriladi(self):
        n = naqsh_yarat(kalit="sozana-novda")
        self.assertEqual(n.fayl_yoli, "taklif/naqshlar/sozana-novda.webp")

    def test_katalogdagi_har_bir_naqsh_fayli_mavjud(self):
        """Fayl yo'q bo'lsa collectstatic emas, sahifa yiqiladi —
        ManifestStaticFilesStorage topilmagan faylga xato beradi."""
        from pathlib import Path

        from django.conf import settings

        papka = Path(settings.BASE_DIR) / "taklif" / "static" / "taklif" / "naqshlar"
        for fayl in papka.glob("*.webp"):
            self.assertTrue(fayl.stat().st_size > 0, f"bo'sh fayl: {fayl.name}")


class NaqshsizSahifalarTest(TestCase):
    """Regressiya: naqsh bloki "taklifnoma" yo'q sahifalarni yiqitmasin.

    Filtr ARGUMENTI mavjud bo'lmagan o'zgaruvchiga ishora qilganda
    Django uni bo'sh deb hisoblamaydi — VariableDoesNotExist ko'taradi.
    Bir paytlar shu sabab 404 sahifasi ham, bosh sahifa ham yiqilgan edi.
    """

    def test_bosh_sahifa_ochiladi(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_topilmadi_sahifasi_ochiladi(self):
        javob = self.client.get("/bunday-sahifa-yoq-12345/")
        self.assertEqual(javob.status_code, 404)
