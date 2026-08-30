"""RSVP yuborish oqimi — audit paytida topilgan ikkita real xatoning
regressiyaga qarshi testlari:
1) Bitta mehmon bir necha marta yuborsa, mehmonlar soni ko'paymasligi kerak.
2) Uzun matn (izoh/ism) production'da (PostgreSQL) 500-xato bermasligi kerak.
"""
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import RSVP, Mehmon, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class RsvpTakrorlanishTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="rsvp-sinov", ism_1="RsvpSinov", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )

    def test_shaxsiy_link_orqali_takroriy_yuborish_bitta_yozuv_qoladi(self):
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Aziz oila")
        c = Client()
        for _ in range(3):
            c.post(f"/{self.taklifnoma.slug}/rsvp/", {
                "ism": "Aziz oila", "keladi": "ha",
                "mehmon_slug": mehmon.slug, "mehmonlar_soni": 4,
            })
        self.assertEqual(RSVP.objects.filter(taklifnoma=self.taklifnoma, mehmon=mehmon).count(), 1)
        self.taklifnoma.refresh_from_db()
        self.assertEqual(self.taklifnoma.keladiganlar_soni, 4)

    def test_shaxsiy_link_orqali_javobni_ozgartirish_yangilanadi(self):
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Karim")
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Karim", "keladi": "ha", "mehmon_slug": mehmon.slug, "mehmonlar_soni": 2})
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Karim", "keladi": "yoq", "mehmon_slug": mehmon.slug, "mehmonlar_soni": 2})
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma, mehmon=mehmon)
        self.assertFalse(yozuv.keladi)

    def test_shaxsiy_linksiz_takroriy_yuborish_sessiya_orqali_yangilanadi(self):
        c = Client()
        for _ in range(3):
            c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Nomsiz", "keladi": "ha", "mehmonlar_soni": 2})
        self.assertEqual(RSVP.objects.filter(taklifnoma=self.taklifnoma, mehmon__isnull=True).count(), 1)

    def test_ikki_xil_mehmon_alohida_yozuv_qoladi(self):
        c1, c2 = Client(), Client()
        c1.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Birinchi", "keladi": "ha", "mehmonlar_soni": 1})
        c2.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Ikkinchi", "keladi": "ha", "mehmonlar_soni": 1})
        self.assertEqual(RSVP.objects.filter(taklifnoma=self.taklifnoma, mehmon__isnull=True).count(), 2)


@override_settings(ALLOWED_HOSTS=["testserver"])
class RsvpUzunMatnTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="uzun-matn-sinov", ism_1="UzunMatn", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )

    def test_uzun_izoh_kesib_saqlanadi_xato_bermaydi(self):
        c = Client()
        r = c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Test", "keladi": "ha", "izoh": "x" * 500, "mehmonlar_soni": 1,
        })
        self.assertEqual(r.status_code, 302)
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma)
        self.assertLessEqual(len(yozuv.izoh), 300)  # model max_length

    def test_uzun_ism_kesib_saqlanadi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "a" * 200, "keladi": "ha", "mehmonlar_soni": 1})
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma)
        self.assertLessEqual(len(yozuv.ism), 100)

    def test_ismsiz_yuborilsa_xato_beriladi_yozuv_yaratilmaydi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "", "keladi": "ha", "mehmonlar_soni": 1})
        self.assertFalse(RSVP.objects.filter(taklifnoma=self.taklifnoma).exists())

    def test_mehmonlar_soni_1_dan_5_gacha_cheklanadi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Ko'p", "keladi": "ha", "mehmonlar_soni": 999})
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma)
        self.assertEqual(yozuv.mehmonlar_soni, 5)
