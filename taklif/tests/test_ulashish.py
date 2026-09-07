"""Ulashish kartochkasi (og:image) uchun testlar.

Bu rasmni MEHMON emas, Telegram/WhatsApp roboti oladi — ya'ni hech kim
uni ko'z bilan tekshirmaydi va buzilib qolsa, bu faqat mijoz havolani
ulashganda, ya'ni eng muhim daqiqada bilinadi. Shu sabab asosiy yo'llar
testda qotirib qo'yilgan.
"""
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Taklifnoma
from taklif.tests.yordamchi import shablon_yarat
from taklif.ulashish import PALITRA, kesh_kaliti


@override_settings(ALLOWED_HOSTS=["testserver"])
class UlashishKartochkasiTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="ulashish-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=self.shablon, sana=timezone.now() + timedelta(days=30),
            toyxona="Anhor", faol=True, tolangan=True,
        )

    def test_rasm_qaytadi(self):
        javob = Client().get(f"/ulashish/{self.taklifnoma.slug}.jpg")
        self.assertEqual(javob.status_code, 200)
        self.assertEqual(javob["Content-Type"], "image/jpeg")
        # JPEG imzosi — javob haqiqatan rasm ekanini tekshiradi (bo'sh yoki
        # xato sahifasi emas).
        self.assertTrue(javob.content.startswith(b"\xff\xd8\xff"))
        self.assertGreater(len(javob.content), 5000)

    def test_notogri_til_saytni_buzmaydi(self):
        # "?t=" tashqaridan keladi — robot ham, odam ham istalgan qiymat
        # yozishi mumkin. Noma'lum til standart tilga tushishi kerak.
        javob = Client().get(f"/ulashish/{self.taklifnoma.slug}.jpg?t=xx-buzuq")
        self.assertEqual(javob.status_code, 200)

    def test_yoq_taklifnoma_404(self):
        self.assertEqual(Client().get("/ulashish/bunday-yoq.jpg").status_code, 404)

    def test_faollashtirilmagan_taklifnomada_ham_ishlaydi(self):
        # Mijoz to'lovdan oldin havolani ulashib ko'rishi mumkin —
        # oldindan ko'rinish o'shanda ham chiqishi kerak.
        self.taklifnoma.tolangan = False
        self.taklifnoma.save()
        self.assertEqual(
            Client().get(f"/ulashish/{self.taklifnoma.slug}.jpg").status_code, 200
        )

    def test_sahifada_og_image_kartochkaga_ishora_qiladi(self):
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        self.assertIn(f"/ulashish/{self.taklifnoma.slug}.jpg?t=", h)
        self.assertNotIn("og-rasm.png", h)

    def test_mazmun_ozgarsa_kesh_kaliti_ham_ozgaradi(self):
        eski = kesh_kaliti(self.taklifnoma, "uz")
        self.taklifnoma.ism_2 = "Nilufar"
        self.assertNotEqual(eski, kesh_kaliti(self.taklifnoma, "uz"))
        # Til ham kalitning bir qismi — aks holda ruscha so'rov o'zbekcha
        # rasmni olib qolardi.
        self.assertNotEqual(
            kesh_kaliti(self.taklifnoma, "uz"), kesh_kaliti(self.taklifnoma, "ru")
        )

    def test_har_bir_dizayn_palitrada_bor(self):
        """Yangi dizayn qo'shilganda palitrasini qo'shish ham esdan
        chiqmasin — aks holda kartochka brend ranglarida chiziladi va
        dizaynning o'ziga xosligi yo'qoladi."""
        from taklif.models import Shablon

        yoq = [k for k in Shablon.objects.values_list("kod", flat=True) if k not in PALITRA]
        self.assertEqual(yoq, [], f"Palitrasi yo'q dizayn(lar): {yoq}")
