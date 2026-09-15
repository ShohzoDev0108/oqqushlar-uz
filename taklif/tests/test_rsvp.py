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

    def test_shaxsiy_linksiz_sessiya_yoqolsa_ham_ism_boyicha_yangilanadi(self):
        """TAFTISH TOPILMASI (2026-09-14): oldin sessiya yagona zaxira edi —
        cookie tozalansa/boshqa brauzerdan kirsa, xohlagancha yangi qator
        qo'sha olardi. Endi bir xil ism bo'yicha bazadan ham tekshiriladi."""
        birinchi, ikkinchi = Client(), Client()  # ikkita MUSTAQIL sessiya
        birinchi.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Bir Xil Ism", "keladi": "ha", "mehmonlar_soni": 3,
        })
        # Katta-kichik harf va sessiya farqiga qaramay — bitta yozuv qoladi,
        # eskisi yangilanadi (soni endi 1 ga o'zgargan bo'lishi kerak).
        ikkinchi.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "bir xil ism", "keladi": "ha", "mehmonlar_soni": 1,
        })
        self.assertEqual(RSVP.objects.filter(taklifnoma=self.taklifnoma, mehmon__isnull=True).count(), 1)
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma, mehmon__isnull=True)
        self.assertEqual(yozuv.mehmonlar_soni, 1)


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

    def test_uzun_tilak_kesib_saqlanadi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Test", "keladi": "ha", "tilak": "x" * 700, "mehmonlar_soni": 1,
        })
        yozuv = RSVP.objects.get(taklifnoma=self.taklifnoma)
        self.assertLessEqual(len(yozuv.tilak), 500)  # model max_length


@override_settings(ALLOWED_HOSTS=["testserver"])
class TilakOmmaviyKorinishiTest(TestCase):
    """Taftish topilmasi: mehmonlar taklifnomaga tilak/tabrik yozish
    imkoniyatiga ega emas edi. Endi RSVP formasidagi "tilak" maydoni
    (izohdan farqli — u faqat mezbonga) yozilsa — LEKIN darhol emas:
    mijoz (mezbon) buni avval statistika sahifasida ko'radi va faqat
    o'zi tasdiqlagach, taklifnoma sahifasida hammaga ochiq bo'ladi.
    Sabab: havolani bilgan har kim (masalan sobiq sevgilisi) yomon
    niyat bilan yozishi mumkin."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="tilak-sinov", ism_1="TilakSinov", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )

    # DIQQAT: apostrof ishlatilmaydi — Django avtomatik HTML-escaping uni
    # "&#x27;" ga aylantiradi, aynan matn qidirilsa test yolg'ondan
    # muvaffaqiyatsiz chiqadi (boshqa testlarda ham shu naqsh qo'llanilgan).

    def test_yangi_tilak_tasdiqlanmaguncha_ommaga_korinmaydi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Muborak", "keladi": "ha", "tilak": "Baxtli oila bolinglar",
            "mehmonlar_soni": 1,
        })
        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertNotContains(r, "Baxtli oila bolinglar")
        self.assertNotContains(r, "Tilaklar")  # bo'lim o'zi ham chiqmasligi kerak

    def test_tasdiqlangach_ommaga_korinadi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Muborak", "keladi": "ha", "tilak": "Baxtli oila bolinglar",
            "mehmonlar_soni": 1,
        })
        javob = RSVP.objects.get(taklifnoma=self.taklifnoma, ism="Muborak")
        self.assertFalse(javob.tilak_tasdiqlangan)  # standart holatda o'chiq

        Client().post(f"/statistika/{self.taklifnoma.statistika_token}/tilak/{javob.pk}/")
        javob.refresh_from_db()
        self.assertTrue(javob.tilak_tasdiqlangan)

        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertContains(r, "Baxtli oila bolinglar")
        self.assertContains(r, "Muborak")

    def test_qaytadan_bosilsa_yashiriladi(self):
        # Tugma ikkala holatda ham shu bitta manzilga POST qiladi —
        # ikkinchi marta bosilsa, qayta yashirilishi kerak.
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Ikki marta", "keladi": "ha", "tilak": "Tabriklayman",
            "mehmonlar_soni": 1,
        })
        javob = RSVP.objects.get(taklifnoma=self.taklifnoma, ism="Ikki marta")
        tasdiqlash_url = f"/statistika/{self.taklifnoma.statistika_token}/tilak/{javob.pk}/"
        Client().post(tasdiqlash_url)
        Client().post(tasdiqlash_url)
        javob.refresh_from_db()
        self.assertFalse(javob.tilak_tasdiqlangan)

    def test_matn_ozgarsa_eski_tasdiq_bekor_boladi(self):
        # Mezbon bir marta tasdiqlagan bo'lsa-yu, keyin (masalan o'sha
        # shaxsiy link orqali) tilak matni butunlay boshqasiga
        # almashtirilsa — eski tasdiq bilan avtomatik ochiq qolib
        # ketmasligi kerak, qayta tasdiqlash talab qilinadi.
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Almashtiruvchi")
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Almashtiruvchi", "keladi": "ha", "tilak": "Yaxshi tilak",
            "mehmon_slug": mehmon.slug, "mehmonlar_soni": 1,
        })
        javob = RSVP.objects.get(taklifnoma=self.taklifnoma, mehmon=mehmon)
        Client().post(f"/statistika/{self.taklifnoma.statistika_token}/tilak/{javob.pk}/")
        javob.refresh_from_db()
        self.assertTrue(javob.tilak_tasdiqlangan)

        # Endi matnni almashtiradi
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Almashtiruvchi", "keladi": "ha", "tilak": "Butunlay boshqa matn",
            "mehmon_slug": mehmon.slug, "mehmonlar_soni": 1,
        })
        javob.refresh_from_db()
        self.assertFalse(javob.tilak_tasdiqlangan)

    def test_tilaksiz_javob_tilaklar_royxatida_chiqmaydi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {"ism": "Sokin", "keladi": "ha", "mehmonlar_soni": 1})
        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertNotContains(r, "Tilaklar")

    def test_izoh_ommaga_ochiq_sahifada_korinmaydi(self):
        # "izoh" (masalan allergiya) faqat mezbonga — ommaviy sahifada
        # hech qachon chiqmasligi kerak.
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Maxfiy", "keladi": "ha", "izoh": "yeryong'oqqa allergiyam bor",
            "mehmonlar_soni": 1,
        })
        r = Client().get(f"/{self.taklifnoma.slug}/")
        self.assertNotContains(r, "allergiyam")

    def test_notogri_token_bilan_tasdiqlab_bolmaydi(self):
        c = Client()
        c.post(f"/{self.taklifnoma.slug}/rsvp/", {
            "ism": "Xavfsizlik", "keladi": "ha", "tilak": "Sinov",
            "mehmonlar_soni": 1,
        })
        javob = RSVP.objects.get(taklifnoma=self.taklifnoma, ism="Xavfsizlik")
        r = Client().post(f"/statistika/notogri-token/tilak/{javob.pk}/")
        self.assertEqual(r.status_code, 404)
        javob.refresh_from_db()
        self.assertFalse(javob.tilak_tasdiqlangan)
