"""Sana har bir tilning o'z qoidasi bo'yicha yozilishini tekshiradi.

Muammo shundan boshlangan: shablonlarda format `date:"d-F, Y"` deb qat'iy
yozilgan edi va rus tilida "12-Октябрь, 2026" degan g'aliz matn chiqardi
(to'g'risi "12 октября 2026" — oy qaratqich kelishikda).

Tekshirgan sari boshqa tillarda ham kamchiliklar chiqdi: qoraqalpoq tilida
o'zbekcha oy nomlari ko'rinardi ("oktabr", holbuki qoraqalpoqchada
"oktyabr"), turkman va qirg'iz tillarida esa sanaga qo'shiladigan
qo'shimchalar umuman yo'q edi.

Endi har bir til uchun alohida jadval bor ("taklif/sana.py"). Quyidagi
jadval — o'sha ishning butun mazmuni. Har bir qator o'sha tildagi rasmiy
matnlardan (davlat organlari saytlari, qonun matnlari, milliy axborot
agentliklari) olingan; manbalar "taklif/sana.py" ichidagi izohlarda.
"""
from datetime import date, timedelta

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone, translation

from taklif.models import Taklifnoma
from taklif.sana import QURUVCHILAR, _turkman_tartib, uzun_sana
from taklif.tests.yordamchi import shablon_yarat

SANA = date(2026, 10, 12)

KUTILGAN = {
    "uz": "2026-yil 12-oktabr",
    "kaa": "2026-jıl 12-oktyabr",
    "ru": "12 октября 2026",
    "tg": "12-уми октябри соли 2026",
    "kk": "2026 жылғы 12 қазан",
    "ky": "2026-жылдын 12-октябры",
    "tk": "2026-njy ýylyň 12-nji oktýabry",
    "en": "12 October 2026",
}


class UzunSanaTest(TestCase):
    def test_har_bir_tilda_kutilgan_natija(self):
        for til, kutilgan in KUTILGAN.items():
            with self.subTest(til=til):
                self.assertEqual(uzun_sana(SANA, til), kutilgan)

    def test_joriy_tildan_oladi(self):
        """Til aniq berilmasa, faol tildan olinishi kerak — shablonlar
        aynan shu yo'l bilan ishlaydi."""
        with translation.override("ru"):
            self.assertEqual(uzun_sana(SANA), KUTILGAN["ru"])

    def test_barcha_sayt_tillari_qamrab_olingan(self):
        """Saytga yangi til qo'shilsa, unga jadval ham yozilishi kerak."""
        sayt_tillari = {kod for kod, _ in settings.LANGUAGES}
        self.assertEqual(sayt_tillari, set(KUTILGAN))
        self.assertEqual(sayt_tillari, set(QURUVCHILAR))

    def test_notanish_til_yiqitmaydi(self):
        """Kelajakda til qo'shilib, jadval unutilsa — sahifa baribir
        ochilishi kerak (inglizcha shaklga qaytadi)."""
        self.assertEqual(uzun_sana(SANA, "fr"), KUTILGAN["en"])

    def test_hudud_kodli_til_ham_ishlaydi(self):
        """Brauzer "ru-RU" yuborishi mumkin."""
        self.assertEqual(uzun_sana(SANA, "ru-RU"), KUTILGAN["ru"])


class OyJadvallariTest(TestCase):
    """Jadvallarning eng oson yo'qotiladigan tafsilotlari."""

    def test_rus_tilida_qaratqich_shakl(self):
        self.assertIn("октября", uzun_sana(SANA, "ru"))
        self.assertNotIn("Октябрь", uzun_sana(SANA, "ru"))

    def test_qoraqalpoq_ozbekchadan_farq_qiladi(self):
        """Qoraqalpoqchada oy nomlari "y" bilan — "oktyabr", "sentyabr"."""
        self.assertIn("oktyabr", uzun_sana(SANA, "kaa"))
        self.assertIn("sentyabr", uzun_sana(date(2026, 9, 1), "kaa"))
        # O'zbekchada esa "y" YO'Q — ikkalasi chalkashmasligi kerak.
        self.assertIn("oktabr", uzun_sana(SANA, "uz"))
        self.assertNotIn("oktyabr", uzun_sana(SANA, "uz"))

    def test_turkman_aprel_istisnosi(self):
        """"aprel" — old qator unli, shuning uchun "apreli", qolganlari
        "-y" oladi. Bu oson o'tkazib yuboriladigan xato."""
        self.assertIn("apreli", uzun_sana(date(2026, 4, 16), "tk"))
        self.assertIn("marty", uzun_sana(date(2026, 3, 25), "tk"))

    def test_qirgiz_egalik_qoshimchalari(self):
        """Qirg'izchada qo'shimcha uch xil: -ы, -и, -у."""
        self.assertIn("апрели", uzun_sana(date(2026, 4, 30), "ky"))
        self.assertIn("июну", uzun_sana(date(2026, 6, 11), "ky"))
        self.assertIn("августу", uzun_sana(date(2026, 8, 8), "ky"))
        self.assertIn("октябры", uzun_sana(SANA, "ky"))

    def test_tojik_izofa(self):
        self.assertIn("октябри", uzun_sana(SANA, "tg"))
        # "май" izofada "майи" bo'ladi — "й" saqlanadi.
        self.assertIn("майи", uzun_sana(date(2026, 5, 31), "tg"))

    def test_qozoqcha_chiziqchasiz(self):
        """Qozoq tilida kun raqamidan keyin chiziqcha ishlatilmaydi —
        qirg'iz va qoraqalpoqdan farqi shunda."""
        self.assertEqual(uzun_sana(SANA, "kk"), "2026 жылғы 12 қазан")
        self.assertNotIn("12-", uzun_sana(SANA, "kk"))

    def test_hamma_oy_hamma_tilda_ishlaydi(self):
        """Jadvalda oy tushib qolmaganini tekshiradi."""
        for til in KUTILGAN:
            for oy in range(1, 13):
                with self.subTest(til=til, oy=oy):
                    natija = uzun_sana(date(2026, oy, 15), til)
                    self.assertTrue(natija.strip())
                    self.assertIn("2026", natija)


class TurkmanTartibSonTest(TestCase):
    """Turkman tartib son qo'shimchasi: "-njy" faqat 6, 9, 10, 30 bilan
    tugagan sonlarda. Qolgan hamma joyda "-nji"."""

    NJY_KUNLAR = {6, 9, 10, 16, 19, 26, 29, 30}

    def test_kunlar(self):
        for kun in range(1, 32):
            kutilgan = "njy" if kun in self.NJY_KUNLAR else "nji"
            with self.subTest(kun=kun):
                self.assertEqual(_turkman_tartib(kun), kutilgan)

    def test_yillar(self):
        # 2010 "-njy", 2020 esa "-nji" — bu juftlik qoidaning raqamga emas,
        # aytilgan so'zga ("on" / "ýigrimi") bog'liqligini isbotlaydi.
        self.assertEqual(_turkman_tartib(2010), "njy")
        self.assertEqual(_turkman_tartib(2020), "nji")
        self.assertEqual(_turkman_tartib(2026), "njy")
        self.assertEqual(_turkman_tartib(2025), "nji")
        self.assertEqual(_turkman_tartib(2000), "nji")


class ShablonlardaQotibQolganFormatYoqTest(TestCase):
    """Yangi shablon yozilganda eski format nusxalanib ketmasligi uchun."""

    def test_shablonlarda_eski_format_qolmagan(self):
        from pathlib import Path

        baza = Path(settings.BASE_DIR)
        topilgan = []
        for papka in ("taklif/templates", "templates"):
            for yol in (baza / papka).rglob("*.html"):
                matn = yol.read_text(encoding="utf-8")
                if 'date:"d-F, Y"' in matn or 'date:"DATE_FORMAT"' in matn:
                    topilgan.append(str(yol.relative_to(baza)))
        self.assertEqual(topilgan, [], f"Eski format qolib ketgan: {topilgan}")


@override_settings(ALLOWED_HOSTS=["testserver"])
class SahifadaSanaTest(TestCase):
    """Yuqoridagi testlar sananing o'zini tekshiradi, bu esa uning
    shablongacha yetib borishini."""

    def setUp(self):
        self.taklifnoma = Taklifnoma.objects.create(
            slug="sana-formati-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=shablon_yarat(),
            sana=timezone.now() + timedelta(days=40),
            faol=True, tolangan=True,
        )
        self.mahalliy = timezone.localtime(self.taklifnoma.sana)

    def test_model_xossasi(self):
        with translation.override("ru"):
            self.assertEqual(
                self.taklifnoma.sana_uzun, uzun_sana(self.mahalliy, "ru")
            )

    def test_ruscha_sahifada_ruscha_shakl(self):
        h = Client().get(
            f"/{self.taklifnoma.slug}/", HTTP_ACCEPT_LANGUAGE="ru"
        ).content.decode()
        self.assertIn(uzun_sana(self.mahalliy, "ru"), h)

    def test_ozbekcha_sahifada_ozbekcha_shakl(self):
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        self.assertIn(uzun_sana(self.mahalliy, "uz"), h)
