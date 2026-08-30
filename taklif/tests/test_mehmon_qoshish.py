"""Mijoz o'zi (admin panelga kirmasdan) statistika sahifasidan turib mehmon
uchun shaxsiy link qo'shishi/o'chirishi — taftish topilmasi: bu funksiya
avval faqat admin panel orqali (mijoz kira olmaydigan joy) ishlar edi."""
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Mehmon, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class MehmonQoshishTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="mehmon-qoshish-sinov", ism_1="MehmonQoshish", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        self.token = self.taklifnoma.statistika_token

    def test_togri_ism_bilan_mehmon_qoshiladi(self):
        r = Client().post(f"/statistika/{self.token}/mehmon-qoshish/", {"ism": "Aziz oila"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Mehmon.objects.filter(taklifnoma=self.taklifnoma, ism="Aziz oila").exists())

    def test_qoshilgan_mehmon_statistika_sahifasida_korinadi(self):
        Client().post(f"/statistika/{self.token}/mehmon-qoshish/", {"ism": "Karim"})
        r = Client().get(f"/statistika/{self.token}/")
        self.assertContains(r, "Karim")

    def test_bosh_ism_bilan_mehmon_qoshilmaydi(self):
        Client().post(f"/statistika/{self.token}/mehmon-qoshish/", {"ism": ""})
        self.assertFalse(Mehmon.objects.filter(taklifnoma=self.taklifnoma).exists())

    def test_notogri_token_404_beradi(self):
        r = Client().post("/statistika/notogri-token-1234/mehmon-qoshish/", {"ism": "Kimdir"})
        self.assertEqual(r.status_code, 404)

    def test_get_sorovi_rad_etiladi(self):
        # @require_POST — faqat forma yuborilganda ishlashi kerak.
        r = Client().get(f"/statistika/{self.token}/mehmon-qoshish/")
        self.assertEqual(r.status_code, 405)


@override_settings(ALLOWED_HOSTS=["testserver"])
class MehmonOchirishTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="mehmon-ochirish-sinov", ism_1="MehmonOchirish", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        self.token = self.taklifnoma.statistika_token
        self.mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Ochiriladigan")

    def test_mehmon_ochiriladi(self):
        r = Client().post(f"/statistika/{self.token}/mehmon-ochirish/{self.mehmon.pk}/")
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Mehmon.objects.filter(pk=self.mehmon.pk).exists())

    def test_boshqa_taklifnoma_tokeni_bilan_ochirib_bolmaydi(self):
        # Bittasi ikkinchisining mehmonini o'z tokeni bilan o'chira olmasligi
        # kerak — "taklifnoma=taklifnoma" filtri shuni kafolatlaydi.
        boshqa = Taklifnoma.objects.create(
            slug="boshqa-taklifnoma", ism_1="Boshqa", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        Client().post(f"/statistika/{boshqa.statistika_token}/mehmon-ochirish/{self.mehmon.pk}/")
        self.assertTrue(Mehmon.objects.filter(pk=self.mehmon.pk).exists())
