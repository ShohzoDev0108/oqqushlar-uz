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

    def test_mening_taklifnomalarim_statistika_linkini_korsatadi(self):
        # Taftish topilmasi: bu ro'yxatda "Statistika" havolasi yo'q edi —
        # mijoz o'z taklifnomasi statistikasini topishning yagona doimiy
        # joyi shu sahifa bo'lishi kerak edi.
        from taklif.views import SESSIYA_KALITI

        client = Client()
        session = client.session
        session[SESSIYA_KALITI] = [self.taklifnoma.slug]
        session.save()
        r = client.get("/mening-taklifnomalarim/")
        self.assertContains(r, self.taklifnoma.get_statistika_url())


@override_settings(ALLOWED_HOSTS=["testserver"])
class OmmaviyKorsatishRoziligiTest(TestCase):
    """Taftish topilmasi: bosh sahifadagi "So'nggi taklifnomalar" bo'limi
    mijozning ismi va marosim sanasini roziliksiz ko'rsatib turgan edi.
    Endi faqat ommaviy_korsatishga_rozi=True bo'lganlar chiqadi."""

    def setUp(self):
        self.shablon = shablon_yarat()

    def test_rozilik_bermagan_taklifnoma_bosh_sahifada_korinmaydi(self):
        Taklifnoma.objects.create(
            slug="rozi-emas", ism_1="RoziEmasIsmi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
            ommaviy_korsatishga_rozi=False,
        )
        r = Client().get("/")
        self.assertNotContains(r, "RoziEmasIsmi")

    def test_rozilik_bergan_taklifnoma_bosh_sahifada_korinadi(self):
        Taklifnoma.objects.create(
            slug="rozi-berdi", ism_1="RoziIsmi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
            ommaviy_korsatishga_rozi=True,
        )
        r = Client().get("/")
        self.assertContains(r, "RoziIsmi")

    def test_standart_holatda_rozilik_ochiq_emas(self):
        t = Taklifnoma.objects.create(
            slug="standart-holat", ism_1="Standart", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        self.assertFalse(t.ommaviy_korsatishga_rozi)


@override_settings(ALLOWED_HOSTS=["testserver"])
class TolanmaganTaklifnomaKorinishiTest(TestCase):
    """Taftish topilmasi: mijoz taklifnoma yaratib, hali to'lamasdan turib
    ham linkni mehmonlarga ulashib yuborishi mumkin edi — `korish`
    funksiyasi faqat "faol"ni tekshirar, "tolangan"ni umuman tekshirmas
    edi. Endi tolangan=False bo'lsa, faqat taklifnomani yaratgan kishining
    o'zi (session orqali — "Mening taklifnomalarim" bilan bir xil ro'yxat)
    ko'ra oladi, boshqa hamma "faollashtirilmagan" sahifasini ko'radi."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="tolanmagan-sinov", ism_1="Tolanmagan", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=False,
        )

    # DIQQAT: "faollashtirilmagan" so'zining o'zini tekshirish orqali emas
    # (bu chiqish shablonlarining CSS klass nomida — ".faollashtirilmagan-
    # banner" — har doim, to'langan bo'lsa ham mavjud), balki faqat shu
    # bloklovchi sahifaga xos "hali tayyor emas" iborasi orqali tekshiramiz.
    BLOKLANGAN_IBORA = "hali tayyor emas"

    def test_tolanmagan_taklifnoma_mehmonga_korinmaydi(self):
        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.BLOKLANGAN_IBORA)
        self.assertNotContains(r, "Tolanmagan")  # mijoz ismi ochilmaydi

    def test_tolanmagan_taklifnoma_korishlar_sonini_oshirmaydi(self):
        Client().get(f"/{self.taklifnoma.slug}/")
        self.taklifnoma.refresh_from_db()
        self.assertEqual(self.taklifnoma.korishlar, 0)

    def test_tolanmagan_taklifnoma_shaxsiy_mehmon_linki_ham_yopiq(self):
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Aziz")
        r = Client().get(f"/{self.taklifnoma.slug}/{mehmon.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.BLOKLANGAN_IBORA)
        mehmon.refresh_from_db()
        self.assertFalse(mehmon.korilgan)

    def test_tolanmagan_taklifnoma_yaratuvchiga_korinadi(self):
        from taklif.views import SESSIYA_KALITI

        client = Client()
        session = client.session
        session[SESSIYA_KALITI] = [self.taklifnoma.slug]
        session.save()
        r = client.get(f"/{self.taklifnoma.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, self.BLOKLANGAN_IBORA)

    def test_tolangan_bolgach_hammaga_korinadi(self):
        self.taklifnoma.tolangan = True
        self.taklifnoma.save()
        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, self.BLOKLANGAN_IBORA)


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
