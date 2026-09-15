"""So'rovlar chegarasi (rate limiting).

TAFTISH TOPILMASI. django-axes faqat LOGIN sahifasini himoya qilardi.
Mijozga ochiq POST manzillari esa butunlay cheklovsiz edi:

  /yaratish/<shablon>/ — har bir so'rov bazaga yozuv qo'shadi va R2'ga
  fayl yuklaydi. Ya'ni bu to'g'ridan-to'g'ri pul: oddiy skript bir
  kechada R2 hisobini ham, bazani ham to'ldirib tashlashi mumkin edi.

  /<slug>/rsvp/ — havolani bilgan har kim mijozning mehmonlar ro'yxatini
  soxta javoblar bilan ko'mib tashlay olardi.

Testlarda kesh HAR SAFAR tozalanadi: aks holda bir test ikkinchisining
hisobini meros qilib olardi va natijalar tartibga bog'liq bo'lib qolardi.
"""
from unittest.mock import MagicMock, patch

from django.core.cache import caches
from django.test import Client, RequestFactory, TestCase, override_settings

from taklif.chegara import YARATISH_CHEGARASI, _bir_vaqtda_faqat_bitta, mijoz_ip
from taklif.models import RSVP, Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat


class IpAniqlashTest(TestCase):
    """Sarlavhaga ishonish — chegarani chetlab o'tishning eng oson yo'li,
    shuning uchun unga faqat ishonchli proksi ortida ishonamiz."""

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(ISHONCHLI_PROKSI=False)
    def test_proksisiz_sarlavhaga_ishonilmaydi(self):
        sorov = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            HTTP_CF_CONNECTING_IP="5.6.7.8",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(mijoz_ip(sorov), "10.0.0.1")

    @override_settings(ISHONCHLI_PROKSI=True)
    def test_cloudflare_sarlavhasi_ustunlik_qiladi(self):
        sorov = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.2.3.4",
            HTTP_CF_CONNECTING_IP="5.6.7.8",
            REMOTE_ADDR="10.0.0.1",
        )
        self.assertEqual(mijoz_ip(sorov), "5.6.7.8")

    @override_settings(ISHONCHLI_PROKSI=True)
    def test_forwarded_forning_birinchi_manzili_olinadi(self):
        sorov = self.factory.get(
            "/", HTTP_X_FORWARDED_FOR="1.2.3.4, 9.9.9.9", REMOTE_ADDR="10.0.0.1"
        )
        self.assertEqual(mijoz_ip(sorov), "1.2.3.4")


@override_settings(ALLOWED_HOSTS=["testserver"], ISHONCHLI_PROKSI=False)
class YaratishChegarasiTest(TestCase):
    def setUp(self):
        caches["chegara"].clear()
        self.shablon = shablon_yarat()
        self.client = Client()

    def _yarat(self, nom):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI, ism_1=nom)
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    def test_chegaradan_keyin_429_qaytadi(self):
        soni, _oyna = YARATISH_CHEGARASI
        for raqam in range(soni):
            javob = self._yarat(f"Mijoz{raqam}")
            self.assertNotEqual(javob.status_code, 429, f"{raqam}-so'rov")

        javob = self._yarat("Ortiqcha")
        self.assertEqual(javob.status_code, 429)
        self.assertFalse(Taklifnoma.objects.filter(ism_1="Ortiqcha").exists())

    def test_boshqa_ip_ozining_hisobiga_ega(self):
        """Chegara IP bo'yicha — bir mijoz boshqasini bloklab qo'ymaydi."""
        soni, _oyna = YARATISH_CHEGARASI
        for raqam in range(soni):
            self._yarat(f"Birinchi{raqam}")

        boshqa = Client(REMOTE_ADDR="203.0.113.7")
        javob = boshqa.post(
            f"/yaratish/{self.shablon.kod}/",
            dict(ASOSIY_FORMA_MAYDONLARI, ism_1="Ikkinchi"),
        )
        self.assertNotEqual(javob.status_code, 429)

    def test_sahifani_ochish_cheklanmaydi(self):
        """GET bepul va zararsiz — uni cheklash qidiruv tizimlariga ham
        xalaqit berardi."""
        soni, _oyna = YARATISH_CHEGARASI
        for raqam in range(soni + 5):
            javob = self.client.get(f"/yaratish/{self.shablon.kod}/")
            self.assertEqual(javob.status_code, 200)

    def test_toxtatilgan_mijozga_ayblovsiz_sahifa_korsatiladi(self):
        """Bu yerga tushadiganlarning ko'pchiligi bot emas, tugmani ikki
        marta bosgan mijoz — ohang qo'rqitmasligi kerak."""
        soni, _oyna = YARATISH_CHEGARASI
        for raqam in range(soni):
            self._yarat(f"M{raqam}")

        javob = self._yarat("Oxirgi")
        self.assertContains(javob, "Biroz kuting", status_code=429)


class BirVaqtdaFaqatBittaTest(TestCase):
    """TAFTISH TOPILMASI (2026-09-14): "o'qi -> tekshir -> yoz" ketma-ketligi
    atomik emas edi — endi PostgreSQL'da pg_advisory_xact_lock bilan
    o'raladi. Mahalliy test muhiti SQLite ishlatgani uchun haqiqiy
    parallellikni sinab bo'lmaydi (bitta jarayon, bitta ulanish) — shu
    bois bu yerda ikkita narsa tekshiriladi: (1) SQLite'da qulf shunchaki
    chetlab o'tilishi (no-op, xatosiz); (2) PostgreSQL vendor'i bilan
    to'g'ri SQL chaqirilishi (haqiqiy Postgres serversiz, mock orqali)."""

    def test_sqlite_da_qulf_shunchaki_otkazib_yuboriladi(self):
        # Mahalliy/test muhiti SQLite bo'lgani uchun bu shart haqiqiy
        # ishlaydi (mock shart emas) — qulfsiz, xatosiz o'tishi kerak.
        bajarildi = False
        with _bir_vaqtda_faqat_bitta("sinov-kaliti"):
            bajarildi = True
        self.assertTrue(bajarildi)

    def test_postgresqlda_advisory_lock_chaqiriladi(self):
        soxta_kursor = MagicMock()
        soxta_ulanish = MagicMock()
        soxta_ulanish.vendor = "postgresql"
        soxta_ulanish.cursor.return_value.__enter__.return_value = soxta_kursor

        with patch("taklif.chegara.db_ulanish", soxta_ulanish), \
             patch("taklif.chegara.transaction.atomic") as atomic_mock:
            atomic_mock.return_value.__enter__.return_value = None
            atomic_mock.return_value.__exit__.return_value = False
            bajarildi = False
            with _bir_vaqtda_faqat_bitta("chegara:yaratish:1.2.3.4"):
                bajarildi = True

        self.assertTrue(bajarildi)
        soxta_kursor.execute.assert_called_once()
        sorov, parametrlar = soxta_kursor.execute.call_args[0]
        self.assertIn("pg_advisory_xact_lock", sorov)
        # Xesh raqami — CRC32, 32-bitli musbat butun son bo'lishi shart.
        self.assertEqual(len(parametrlar), 1)
        self.assertGreaterEqual(parametrlar[0], 0)
        self.assertLess(parametrlar[0], 2**32)


@override_settings(ALLOWED_HOSTS=["testserver"], ISHONCHLI_PROKSI=False)
class RsvpChegarasiTest(TestCase):
    def setUp(self):
        caches["chegara"].clear()
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="chegara-sinovi", ism_1="Mezbon", shablon=self.shablon,
            sana="2027-05-20T18:00", faol=True, tolangan=True,
        )

    def test_soxta_javoblar_oqimi_toxtatiladi(self):
        client = Client()
        manzil = f"/{self.taklifnoma.slug}/rsvp/"
        toxtadi = False
        for raqam in range(60):
            javob = client.post(manzil, {"ism": f"Bot{raqam}", "keladi": "ha"})
            if javob.status_code == 429:
                toxtadi = True
                break
        self.assertTrue(toxtadi, "RSVP chegarasi umuman ishlamadi")
        # To'xtaganidan keyin yangi javob yozilmaydi.
        oldingi = RSVP.objects.count()
        client.post(manzil, {"ism": "Yana bitta", "keladi": "ha"})
        self.assertEqual(RSVP.objects.count(), oldingi)
