"""Mijoz telefon raqami: normallashtirish, majburiyligi va maxfiyligi.

TAFTISH TOPILMASI. Taklifnomada buyurtmachi bilan bog'lanishning hech
qanday yo'li yo'q edi. Bu ikki joyda og'riq berardi:

  1) To'lov. Mijoz taklifnomani yaratadi, keyin Telegram orqali pul
     yuboradi. Admin qaysi to'lov qaysi taklifnomaga tegishli ekanini
     faqat ismga qarab taxmin qilardi.
  2) Kirishni yo'qotish. Egalik faqat brauzer sessiyasi bilan isbotlanadi.
     Brauzer ma'lumoti tozalansa yoki telefon almashtirilsa, mijoz o'z
     mehmonlar ro'yxati va statistikasidan butunlay ayrilardi.

Uchinchi test guruhi — maxfiylik. Raqam MIJOZNIKI, ya'ni u mehmonlar
ko'radigan sahifada paydo bo'lmasligi kerak.
"""
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.forms import telefonni_normallashtir
from taklif.models import Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat


class TelefonniNormallashtirishTest(TestCase):
    """Mijozlar raqamni xilma-xil yozadi — bazada bir xil turishi kerak,
    aks holda admin qidiruvi ishlamaydi."""

    def test_ozbek_raqamining_barcha_korinishlari_bir_xil_boladi(self):
        for xom in (
            "901234567",
            "90 123 45 67",
            "(90) 123-45-67",
            "998901234567",
            "+998 90 123 45 67",
            "+998-90-123-45-67",
        ):
            self.assertEqual(telefonni_normallashtir(xom), "+998901234567", xom)

    def test_chet_el_raqami_ozgartirilmaydi(self):
        """Saytdan chet eldagi mijoz ham foydalanishi mumkin — uning
        raqamini O'zbekiston qolipiga majburlash noto'g'ri."""
        self.assertEqual(telefonni_normallashtir("+7 495 123 45 67"), "+74951234567")

    def test_notogri_raqam_tanilmaydi(self):
        for xom in ("", "   ", "abc", "12345", "9012345678901234567890"):
            self.assertIsNone(telefonni_normallashtir(xom), repr(xom))


@override_settings(ALLOWED_HOSTS=["testserver"])
class FormadaTelefonTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    def _post(self, qoshimcha=None):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        maydonlar["mijoz_telefoni"] = "+998 90 123 45 67"
        if qoshimcha:
            maydonlar.update(qoshimcha)
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    def test_telefon_saqlanadi_va_normallashtiriladi(self):
        self._post({"ism_1": "Telefonli", "mijoz_telefoni": "90 123 45 67"})
        t = Taklifnoma.objects.get(ism_1="Telefonli")
        self.assertEqual(t.mijoz_telefoni, "+998901234567")

    def test_telefonsiz_taklifnoma_yaratilmaydi(self):
        """Raqamsiz to'lovni taklifnomaga bog'lab bo'lmaydi."""
        javob = self._post({"ism_1": "Telefonsiz", "mijoz_telefoni": ""})
        self.assertEqual(javob.status_code, 200)  # redirect emas — forma xatosi
        self.assertFalse(Taklifnoma.objects.filter(ism_1="Telefonsiz").exists())

    def test_notogri_raqam_qabul_qilinmaydi(self):
        javob = self._post({"ism_1": "Xato", "mijoz_telefoni": "123"})
        self.assertEqual(javob.status_code, 200)
        self.assertFalse(Taklifnoma.objects.filter(ism_1="Xato").exists())

    def test_xato_matnida_misol_bor(self):
        """Quruq "noto'g'ri format" mijozni formada qamab qo'yadi —
        nima kutilayotgani misol bilan ko'rsatilishi kerak."""
        javob = self._post({"ism_1": "Xato2", "mijoz_telefoni": "123"})
        self.assertContains(javob, "+998 90 123 45 67")


@override_settings(ALLOWED_HOSTS=["testserver"])
class TelefonMaxfiyligiTest(TestCase):
    """Raqam MIJOZNIKI — mehmonlar ko'radigan sahifada chiqmasligi shart."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="maxfiy-raqam",
            ism_1="Mezbon",
            shablon=self.shablon,
            sana=timezone.now(),
            faol=True,
            tolangan=True,
            mijoz_telefoni="+998901234567",
        )

    def test_taklifnoma_sahifasida_raqam_korinmaydi(self):
        javob = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertEqual(javob.status_code, 200)
        self.assertNotContains(javob, "998901234567")
        self.assertNotContains(javob, "90 123 45 67")


class SessiyaMuddatiTest(TestCase):
    """To'y bir necha oy oldindan tayyorlanadi. Django'ning standart
    ikki haftalik sessiyasi bilan mijoz o'z taklifnomasini boshqarish
    huquqini yo'qotib qo'yardi."""

    def test_sessiya_kamida_bir_yil(self):
        from django.conf import settings

        self.assertGreaterEqual(settings.SESSION_COOKIE_AGE, 60 * 60 * 24 * 365)

    def test_sessiya_har_sorovda_yangilanadi(self):
        from django.conf import settings

        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
