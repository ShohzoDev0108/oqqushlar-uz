"""Asosiy sahifalar uchun tezkor "tutun testi" (smoke test) — sahifa umuman
ochiladimi, kutilgan status kodni qaytaradimi."""
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Mehmon, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class UmumiySahifalarTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="umumiy-sinov", ism_1="Umumiy", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        self.client = Client()

    def test_bosh_sahifa_ochiladi(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_html_lang_atributi_faol_tilni_korsatadi(self):
        # Taftish topilmasi: <html lang="uz"> qattiq yozilgan edi, hatto
        # foydalanuvchi boshqa tilni tanlagan bo'lsa ham. Endi
        # LANGUAGE_CODE'dan olinadi (standart holatda "uz").
        r = self.client.get("/")
        self.assertContains(r, '<html lang="uz"')

    def test_shablon_tanlash_ochiladi(self):
        self.assertEqual(self.client.get("/yaratish/").status_code, 200)

    def test_taklifnoma_korish_ochiladi(self):
        self.assertEqual(self.client.get(f"/{self.taklifnoma.slug}/").status_code, 200)

    def test_faol_emas_taklifnoma_yopilgan_sahifani_korsatadi(self):
        self.taklifnoma.faol = False
        self.taklifnoma.save()
        r = self.client.get(f"/{self.taklifnoma.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "yopilgan")

    def test_mehmon_shaxsiy_link_ochiladi_va_korilgan_deb_belgilanadi(self):
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Aziz")
        r = self.client.get(f"/{self.taklifnoma.slug}/{mehmon.slug}/")
        self.assertEqual(r.status_code, 200)
        mehmon.refresh_from_db()
        self.assertTrue(mehmon.korilgan)

    def test_statistika_sahifasi_token_orqali_ochiladi(self):
        r = self.client.get(f"/statistika/{self.taklifnoma.statistika_token}/")
        self.assertEqual(r.status_code, 200)

    def test_yoqdi_telegramga_yonaltiradi(self):
        r = self.client.get(f"/{self.taklifnoma.slug}/yoqdi/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("t.me/", r.get("Location", ""))
        self.taklifnoma.refresh_from_db()
        self.assertTrue(self.taklifnoma.yoqdi_bosildi)

    def test_mavjud_bolmagan_manzil_404(self):
        r = self.client.get("/shunaqa-sahifa-yoq-albatta/")
        self.assertEqual(r.status_code, 404)

    def test_mening_taklifnomalarim_boshqa_sessiyada_bosh(self):
        r = self.client.get("/mening-taklifnomalarim/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "Umumiy")


@override_settings(ALLOWED_HOSTS=["testserver"])
class AdminManzilTest(TestCase):
    """Audit topilmasi: admin standart /admin/ o'rniga sozlanadigan manzilda."""

    def test_eski_admin_manzili_ishlamaydi(self):
        r = Client().get("/admin/")
        self.assertEqual(r.status_code, 404)

    def test_yangi_admin_manzili_ishlaydi(self):
        from django.conf import settings
        r = Client().get(f"/{settings.ADMIN_URL_YOLI}login/")
        self.assertEqual(r.status_code, 200)
