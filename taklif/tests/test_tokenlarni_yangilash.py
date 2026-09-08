"""`tokenlarni_yangilash` buyrug'i uchun testlar.

Buyruq xavfsizlik hodisasidan keyin yozildi: "Tayyor" sahifasi bir muddat
egalikni tekshirmasdan maxfiy statistika havolasini ko'rsatib turgan edi.
Teshik yopildi, lekin ilgari yig'ilgan tokenlar token o'zgarmagunicha
ishlayverardi. Shu testlar buyruq haqiqatan ham eski tokenni bekor qilishini
va statistika sahifasi endi eski token bilan ochilmasligini tekshiradi.
"""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class TokenlarniYangilashTest(TestCase):
    def setUp(self):
        shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="token-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=shablon, sana=timezone.now() + timedelta(days=20),
            faol=True, tolangan=True,
        )
        self.eski_token = self.taklifnoma.statistika_token

    def _ishga_tushir(self, *argumentlar):
        chiqish = StringIO()
        call_command("tokenlarni_yangilash", *argumentlar, stdout=chiqish)
        return chiqish.getvalue()

    def test_token_ozgaradi(self):
        self._ishga_tushir("--sorasin-mas")
        self.taklifnoma.refresh_from_db()
        self.assertNotEqual(self.taklifnoma.statistika_token, self.eski_token)

    def test_yangi_token_toliq_uzunlikda(self):
        """token_hex() 32 bayt = 64 hex belgi. Agar kimdir kelajakda
        token_hex(16) ga o'zgartirsa, maydon qisqarib xavfsizlik pasayadi."""
        self._ishga_tushir("--sorasin-mas")
        self.taklifnoma.refresh_from_db()
        self.assertEqual(len(self.taklifnoma.statistika_token), 64)

    def test_eski_havola_endi_ochilmaydi(self):
        """Buyruqning butun mazmuni shu — eski havola o'lishi kerak."""
        c = Client()
        self.assertEqual(c.get(f"/statistika/{self.eski_token}/").status_code, 200)
        self._ishga_tushir("--sorasin-mas")
        self.assertEqual(c.get(f"/statistika/{self.eski_token}/").status_code, 404)

    def test_yangi_havola_ishlaydi(self):
        self._ishga_tushir("--sorasin-mas")
        self.taklifnoma.refresh_from_db()
        javob = Client().get(f"/statistika/{self.taklifnoma.statistika_token}/")
        self.assertEqual(javob.status_code, 200)

    def test_hamma_yozuv_yangilanadi(self):
        shablon = shablon_yarat()
        ikkinchi = Taklifnoma.objects.create(
            slug="token-sinov-2", ism_1="Aziz",
            shablon=shablon, sana=timezone.now() + timedelta(days=30),
        )
        eski_ikkinchi = ikkinchi.statistika_token

        self._ishga_tushir("--sorasin-mas")

        self.taklifnoma.refresh_from_db()
        ikkinchi.refresh_from_db()
        self.assertNotEqual(self.taklifnoma.statistika_token, self.eski_token)
        self.assertNotEqual(ikkinchi.statistika_token, eski_ikkinchi)
        # Tokenlar bir-biridan ham farq qilishi kerak (unique cheklovi).
        self.assertNotEqual(
            self.taklifnoma.statistika_token, ikkinchi.statistika_token
        )

    def test_sinov_rejimi_hech_narsa_ozgartirmaydi(self):
        chiqish = self._ishga_tushir("--sinov")
        self.taklifnoma.refresh_from_db()
        self.assertEqual(self.taklifnoma.statistika_token, self.eski_token)
        self.assertIn("SINOV", chiqish)

    def test_bosh_bazada_yiqilmaydi(self):
        Taklifnoma.objects.all().delete()
        chiqish = self._ishga_tushir("--sorasin-mas")
        self.assertIn("yo'q", chiqish)
