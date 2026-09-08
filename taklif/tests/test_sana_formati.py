"""Sana formati har bir tilda to'g'ri chiqishini tekshiradi.

Muammo shundan boshlangan: shablonlarda format `date:"d-F, Y"` deb qat'iy
yozilgan edi. `F` — oyning bosh kelishikdagi nomi. O'zbekchada bu to'g'ri
("12-Oktabr, 2026"), lekin rus tilida sana ichida oy qaratqich kelishigida
keladi — "12 октября 2026". Bizda esa "12-Октябрь, 2026" chiqardi.

Endi format har bir til uchun alohida belgilangan (config/formats/), shablon
esa `date:"DATE_FORMAT"` deb yozadi. Shu testlar o'sha formatlar haqiqatan
kutilgan natijani berishini va shablonlarda eski qat'iy format qolib
ketmaganini kuzatib turadi.
"""
from datetime import date, timedelta
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone, translation
from django.utils.formats import date_format

from taklif.models import Taklifnoma
from taklif.tests.yordamchi import shablon_yarat

SANA = date(2026, 10, 12)

# Har bir til uchun kutilgan natija. Bu jadval — shu o'zgarishning butun
# mazmuni: kimdir formatni o'zgartirsa, shu yerda ko'rinadi.
KUTILGAN = {
    "uz": "12-Oktabr, 2026",
    "kaa": "12-Oktabr, 2026",
    "ru": "12 октября 2026",
    "tg": "12 октябр 2026",
    "kk": "12 Қазан 2026",
    "ky": "12 Октябрь 2026",
    "tk": "12 Oktýabr 2026",
    "en": "12 October 2026",
}


class SanaFormatiTest(TestCase):
    def test_har_bir_tilda_kutilgan_natija(self):
        for til, kutilgan in KUTILGAN.items():
            with self.subTest(til=til), translation.override(til):
                self.assertEqual(date_format(SANA, "DATE_FORMAT"), kutilgan)

    def test_barcha_tillar_qamrab_olingan(self):
        """Saytga yangi til qo'shilsa, unga format ham belgilanishi kerak —
        aks holda Django o'zining standart formatiga qaytadi (masalan rus
        tilida oxiriga "г." qo'shib qo'yadi)."""
        sayt_tillari = {kod for kod, _ in settings.LANGUAGES}
        self.assertEqual(sayt_tillari, set(KUTILGAN))
        for til in sayt_tillari:
            yol = Path(settings.BASE_DIR) / "config" / "formats" / til / "formats.py"
            self.assertTrue(yol.exists(), f"{til} uchun format fayli yo'q")

    def test_rus_tilida_qaratqich_shakl(self):
        """Eng muhimi — aynan shu xato tuzatildi."""
        with translation.override("ru"):
            natija = date_format(SANA, "DATE_FORMAT")
        self.assertIn("октября", natija)
        self.assertNotIn("Октябрь", natija)

    def test_kalendar_bloki_bosh_kelishikda_qoladi(self):
        """Kalendar blokida oy YAKKA turadi ("Октябрь 2026") — u yerda bosh
        kelishik to'g'ri, shuning uchun u format o'zgarishiga qo'shilmagan."""
        with translation.override("ru"):
            self.assertEqual(date_format(SANA, "F Y"), "Октябрь 2026")


class ShablonlardaQotibQolganFormatYoqTest(TestCase):
    """Yangi shablon yozilganda eski format nusxalanib ketmasligi uchun."""

    ESKI = 'date:"d-F, Y"'

    def test_shablonlarda_eski_format_qolmagan(self):
        baza = Path(settings.BASE_DIR)
        topilgan = []
        for papka in ("taklif/templates", "templates"):
            for yol in (baza / papka).rglob("*.html"):
                if self.ESKI in yol.read_text(encoding="utf-8"):
                    topilgan.append(str(yol.relative_to(baza)))
        self.assertEqual(topilgan, [], f"Eski format qolib ketgan: {topilgan}")


@override_settings(ALLOWED_HOSTS=["testserver"])
class SahifadaSanaTest(TestCase):
    """Format haqiqiy taklifnoma sahifasida ham qo'llanishini tekshiradi —
    yuqoridagi testlar formatning o'zini, bu esa uning shablongacha
    yetib borishini kuzatadi."""

    def setUp(self):
        self.taklifnoma = Taklifnoma.objects.create(
            slug="sana-formati-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=shablon_yarat(),
            sana=timezone.now() + timedelta(days=40),
            faol=True, tolangan=True,
        )
        with translation.override("ru"):
            self.kutilgan_ru = date_format(
                timezone.localtime(self.taklifnoma.sana), "DATE_FORMAT"
            )
        with translation.override("uz"):
            self.kutilgan_uz = date_format(
                timezone.localtime(self.taklifnoma.sana), "DATE_FORMAT"
            )

    def test_ruscha_sahifada_ruscha_format(self):
        h = Client().get(
            f"/{self.taklifnoma.slug}/", HTTP_ACCEPT_LANGUAGE="ru"
        ).content.decode()
        self.assertIn(self.kutilgan_ru, h)

    def test_ozbekcha_sahifada_ozbekcha_format(self):
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        self.assertIn(self.kutilgan_uz, h)
