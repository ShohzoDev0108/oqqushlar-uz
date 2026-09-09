"""Ommaviy oferta va maxfiylik siyosati sahifalari.

TAFTISH TOPILMASI. Sayt pul qabul qilardi va mijozlarning ismlarini
saqlardi, lekin na ommaviy oferta, na maxfiylik siyosati bor edi. Endi
mijoz telefon raqami ham yig'iladi — ya'ni bu hujjatlar shunchaki foydali
emas, majburiy.

Bu testlar hujjatlarning MAZMUNINI baholamaydi (buni yurist qiladi).
Ular ikki narsani qo'riqlaydi: hujjat mavjudligi va topilishi, hamda
rozilik olinmasdan taklifnoma yaratilmasligi.
"""
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from taklif.models import SaytSozlamalari, Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class HuquqiySahifalarTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_ikkala_sahifa_ochiladi(self):
        for nom in ("taklif:ommaviy_oferta", "taklif:maxfiylik_siyosati"):
            javob = self.client.get(reverse(nom))
            self.assertEqual(javob.status_code, 200, nom)

    def test_footerdan_topiladi(self):
        """Huquqiy hujjat har bir sahifadan bir bosishda topilishi kerak."""
        javob = self.client.get("/")
        self.assertContains(javob, reverse("taklif:ommaviy_oferta"))
        self.assertContains(javob, reverse("taklif:maxfiylik_siyosati"))

    def test_rus_tilida_oz_tarjimasi_korsatiladi(self):
        javob = self.client.get(
            reverse("taklif:ommaviy_oferta"), headers={"accept-language": "ru"}
        )
        self.assertContains(javob, "публичной офертой")

    def test_tarjimasiz_tilda_ozbekcha_matn_va_ochiq_izoh(self):
        """Jimgina boshqa tilda matn berish mijozni chalg'itadi — sahifa
        matn qaysi tilda ekanini ochiq aytishi kerak."""
        javob = self.client.get(
            reverse("taklif:maxfiylik_siyosati"), headers={"accept-language": "tk"}
        )
        self.assertEqual(javob.status_code, 200)
        # Uslub bloki ham shu sinf nomini o'z ichiga oladi — shuning uchun
        # aynan CHIQARILGAN blokni qidiramiz.
        self.assertContains(javob, '<p class="hq-tarjima-izoh">')


@override_settings(ALLOWED_HOSTS=["testserver"])
class RekvizitlarTest(TestCase):
    """Nomsiz oferta huquqiy jihatdan bo'sh qog'oz. Chala jadval
    ko'rsatgandan ko'ra umuman ko'rsatmagan ma'qul."""

    def test_rekvizitlar_toldirilmagan_bolsa_bolim_chiqmaydi(self):
        javob = Client().get(reverse("taklif:ommaviy_oferta"))
        self.assertNotContains(javob, '<div class="hq-rekvizit">')

    def test_toldirilgan_rekvizitlar_korsatiladi(self):
        sozlama = SaytSozlamalari.olish()
        sozlama.tashkilot_nomi = "Sinov YaTT"
        sozlama.stir = "123456789"
        sozlama.save()

        javob = Client().get(reverse("taklif:ommaviy_oferta"))
        self.assertContains(javob, "Sinov YaTT")
        self.assertContains(javob, "123456789")


@override_settings(ALLOWED_HOSTS=["testserver"])
class ShartlargaRozilikTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    def _post(self, qoshimcha=None):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        if qoshimcha:
            maydonlar.update(qoshimcha)
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    def test_rozilik_belgilanmasa_taklifnoma_yaratilmaydi(self):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        maydonlar.pop("shartlarga_rozi")  # brauzer belgilanmagan katakchani yubormaydi
        maydonlar["ism_1"] = "Rozisiz"
        javob = self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

        self.assertEqual(javob.status_code, 200)
        self.assertFalse(Taklifnoma.objects.filter(ism_1="Rozisiz").exists())

    def test_rozilik_bazada_saqlanadi(self):
        """Rozilikning O'ZI dalil: nizo chiqsa "shartlarni ko'rsatgan edik"
        degan gap yetarli emas."""
        self._post({"ism_1": "Rozi"})
        self.assertTrue(Taklifnoma.objects.get(ism_1="Rozi").shartlarga_rozi)

    def test_formada_ikkala_hujjatga_havola_bor(self):
        javob = self.client.get(f"/yaratish/{self.shablon.kod}/")
        self.assertContains(javob, reverse("taklif:ommaviy_oferta"))
        self.assertContains(javob, reverse("taklif:maxfiylik_siyosati"))

    def test_eski_taklifnomalarda_rozilik_belgilanmagan(self):
        """Hujjatlar e'lon qilingunga qadar yaratilganlarni True qilib
        qo'yish yolg'on bo'lardi."""
        eski = Taklifnoma.objects.create(
            slug="eski-yozuv", ism_1="Eski", shablon=self.shablon,
            sana="2027-01-01T18:00", faol=True,
        )
        self.assertFalse(eski.shartlarga_rozi)
