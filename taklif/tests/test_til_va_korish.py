"""Ikkita mustaqil taftish topilmasi uchun testlar:
1) Bitta brauzer/sessiya bir taklifnomani bir necha marta qayta ochsa,
   "ko'rishlar" soni faqat birinchi safar oshishi kerak.
2) Mezbonga tegishli sahifalar (statistika va h.k.) — aniq til tanlanmagan
   bo'lsa — brauzerning "Accept-Language"idan qat'i nazar har doim
   o'zbekcha ko'rsatilishi kerak.
"""
from datetime import timedelta

from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


@override_settings(ALLOWED_HOSTS=["testserver"])
class KorishlarTakrorlanmasligiTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="korish-sinov", ism_1="KorishSinov", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )

    def test_bitta_sessiya_qayta_ochsa_bitta_korish_deb_hisoblanadi(self):
        c = Client()
        for _ in range(20):
            c.get(f"/{self.taklifnoma.slug}/")
        self.taklifnoma.refresh_from_db()
        self.assertEqual(self.taklifnoma.korishlar, 1)

    def test_ikki_xil_sessiya_alohida_korish_deb_hisoblanadi(self):
        Client().get(f"/{self.taklifnoma.slug}/")
        Client().get(f"/{self.taklifnoma.slug}/")
        self.taklifnoma.refresh_from_db()
        self.assertEqual(self.taklifnoma.korishlar, 2)

    def test_boshqa_taklifnoma_alohida_hisoblanadi(self):
        # Sessiyadagi ro'yxat faqat SHU taklifnoma uchun emas — boshqa
        # taklifnomani birinchi marta ko'rsa, u alohida hisoblanishi kerak.
        boshqa = Taklifnoma.objects.create(
            slug="korish-sinov-2", ism_1="Ikkinchi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        c = Client()
        c.get(f"/{self.taklifnoma.slug}/")
        c.get(f"/{self.taklifnoma.slug}/")
        c.get(f"/{boshqa.slug}/")
        self.taklifnoma.refresh_from_db()
        boshqa.refresh_from_db()
        self.assertEqual(self.taklifnoma.korishlar, 1)
        self.assertEqual(boshqa.korishlar, 1)


@override_settings(ALLOWED_HOSTS=["testserver"])
class MezbonTiliStandartTest(TestCase):
    """Taftish topilmasi: mijoz statistika sahifasini boshqa qurilma/ilovada
    (masalan Telegram ichki brauzerida) ochsa, u yerning "Accept-Language"
    sarlavhasiga qarab til noto'g'ri (masalan ruscha) o'zgarib qolar edi."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="til-sinov", ism_1="TilSinov", shablon=self.shablon,
            # DIQQAT: kelajakdagi sana — RSVP bo'limi (pastdagi testda
            # tekshirilayotgan "tilak" yorlig'i shu formada) endi faqat
            # marosim sanasi hali o'tib ketmagan taklifnomalarda ko'rsatiladi.
            sana=timezone.now() + timedelta(days=30), faol=True, tolangan=True,
        )

    # Diskriminatsiya uchun: bu matnning ruscha tarjimasi mavjud (aks holda
    # tarjima bo'lmasa, Django tarjima qilinmagan matnni asl — o'zbekcha —
    # holida ko'rsatib qo'yadi, va test noto'g'ri "o'tib ketishi" mumkin edi).
    OGOHLANTIRISH_UZ = "Bu sahifa faqat sizga ko'rinadi"
    OGOHLANTIRISH_RU = "Эта страница видна только вам"

    def test_ruscha_brauzer_bilan_ham_statistika_ozbekcha_chiqadi(self):
        r = Client().get(
            f"/statistika/{self.taklifnoma.statistika_token}/",
            HTTP_ACCEPT_LANGUAGE="ru",
        )
        self.assertContains(r, self.OGOHLANTIRISH_UZ)
        self.assertNotContains(r, self.OGOHLANTIRISH_RU)

    def test_ruscha_brauzer_bilan_mening_taklifnomalarim_ozbekcha_chiqadi(self):
        r = Client().get("/mening-taklifnomalarim/", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertContains(r, "Mening taklifnomalarim")
        self.assertNotContains(r, "Мои приглашения")

    def test_aniq_til_tanlansa_statistika_sahifasida_ham_saqlanadi(self):
        # Avval mehmon sahifasida ruschani ANIQ tanlagan (cookie o'rnatiladi) —
        # bu tanlov statistika sahifasida ham hurmat qilinishi kerak.
        c = Client()
        c.post("/i18n/setlang/", {"language": "ru", "next": "/"})
        r = c.get(f"/statistika/{self.taklifnoma.statistika_token}/")
        self.assertContains(r, self.OGOHLANTIRISH_RU)
        self.assertNotContains(r, self.OGOHLANTIRISH_UZ)

    def test_taklifnoma_sahifasi_ozi_bu_middlewarega_taalluqli_emas(self):
        # Mehmonlarga ochiq taklifnoma sahifasi hali ham to'liq avtomatik
        # ko'p tillilikdan foydalanishi kerak (Accept-Language'ga qarab) —
        # bu middleware faqat mezbon sahifalariga taalluqli.
        r = Client().get(f"/{self.taklifnoma.slug}/", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "пожелание")  # "tilak" so'zining ruscha tarjimasi (RSVP formasi yorlig'ida)
