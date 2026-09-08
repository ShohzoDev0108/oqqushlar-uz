"""Sitemap va robots.txt uchun testlar.

Eng muhimi — sayt xaritasiga MIJOZ TAKLIFNOMALARI tushmasligi. Ularda
ism va marosim sanasi bor; sitemap esa Google'ga "mana, bularni
indekslang" degan to'g'ridan-to'g'ri taklif. Kelajakda kimdir xaritaga
yangi bo'lim qo'shsa va tasodifan taklifnomalarni qo'shib yuborsa, shu
test to'xtatadi.
"""
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Shablon, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class SitemapTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        Shablon.objects.filter(pk=self.shablon.pk).update(ommaviy=True)
        self.taklifnoma = Taklifnoma.objects.create(
            slug="sitemap-sinov-taklifnoma", ism_1="Maxfiy", ism_2="Mijoz",
            shablon=self.shablon, sana=timezone.now() + timedelta(days=20),
            faol=True, tolangan=True,
        )

    def test_sitemap_ochiladi(self):
        javob = Client().get("/sitemap.xml")
        self.assertEqual(javob.status_code, 200)
        self.assertIn("xml", javob["Content-Type"])

    def test_asosiy_sahifalar_bor(self):
        h = Client().get("/sitemap.xml").content.decode()
        for yol in ["/dizaynlar/", "/narxlar/", "/savol-javob/",
                    "/biz-haqimizda/", "/boglanish/"]:
            self.assertIn(f"<loc>https://testserver{yol}</loc>", h)

    def test_ommaviy_dizayn_namunasi_bor(self):
        h = Client().get("/sitemap.xml").content.decode()
        self.assertIn(f"/namuna/{self.shablon.kod}/", h)

    def test_ommaviy_bolmagan_dizayn_yoq(self):
        yopiq = Shablon.objects.create(
            nomi="Yopiq", kod="yopiq-dizayn", narx=100000, ommaviy=False
        )
        h = Client().get("/sitemap.xml").content.decode()
        self.assertNotIn(yopiq.kod, h)

    def test_mijoz_taklifnomasi_sitemapda_yoq(self):
        """Eng muhim tekshiruv — pastdagi izohga qarang (fayl boshida)."""
        h = Client().get("/sitemap.xml").content.decode()
        self.assertNotIn(self.taklifnoma.slug, h)
        self.assertNotIn(self.taklifnoma.ism_1, h)


@override_settings(ALLOWED_HOSTS=["testserver"])
class RobotsTest(TestCase):
    def test_robots_ochiladi(self):
        javob = Client().get("/robots.txt")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob["Content-Type"], "text/plain")

    def test_sitemap_korsatilgan(self):
        h = Client().get("/robots.txt").content.decode()
        self.assertIn("Sitemap: https://oqqushlar.uz/sitemap.xml", h)

    def test_shaxsiy_bolimlar_yopilgan(self):
        h = Client().get("/robots.txt").content.decode()
        for bolim in ["/statistika/", "/tayyor/", "/mening-taklifnomalarim/"]:
            self.assertIn(f"Disallow: {bolim}", h)


@override_settings(ALLOWED_HOSTS=["testserver"])
class NoindexTest(TestCase):
    """Mijoz taklifnomalari Google'ga tushmasligi kerak (sabablari
    base.html'dagi izohda). Namuna sahifalari esa AKSINCHA — ular aynan
    indekslanishi kerak, shuning uchun ikkalasi ham tekshiriladi."""

    NOINDEX = 'content="noindex, follow"'

    def setUp(self):
        self.shablon = shablon_yarat()
        Shablon.objects.filter(pk=self.shablon.pk).update(ommaviy=True)
        self.taklifnoma = Taklifnoma.objects.create(
            slug="noindex-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=self.shablon, sana=timezone.now() + timedelta(days=20),
            faol=True, tolangan=True,
        )

    def test_taklifnoma_sahifasi_indekslanmaydi(self):
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        self.assertIn(self.NOINDEX, h)

    def test_faollashtirilmagan_sahifa_indekslanmaydi(self):
        self.taklifnoma.tolangan = False
        self.taklifnoma.save()
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        self.assertIn(self.NOINDEX, h)

    def test_namuna_sahifasi_INDEKSLANADI(self):
        h = Client().get(f"/namuna/{self.shablon.kod}/").content.decode()
        self.assertNotIn(self.NOINDEX, h)

    def test_sayt_sahifalari_INDEKSLANADI(self):
        for yol in ["/", "/dizaynlar/", "/narxlar/", "/savol-javob/"]:
            h = Client().get(yol).content.decode()
            self.assertNotIn(self.NOINDEX, h, f"{yol} yopilib qolgan")
