"""Yaratish formasidagi "eskisini yangilash" tugmasi nimani o'chirishi mumkin.

TAFTISH TOPILMASI. Mijoz xuddi shu ismlar bilan ikkinchi marta taklifnoma
yaratsa, sayt "Buni yangilayman (eskisi o'chadi)" tugmasini ko'rsatardi va
bosilganda `mavjud.delete()` ni SHARTSIZ bajarardi. Ya'ni mijoz allaqachon
to'lagan, mehmonlarga tarqatgan va yuzlab RSVP javobi yig'ilgan taklifnoma
ham o'sha bitta bosishda butunlay yo'q bo'lardi — mehmonlar va javoblar
CASCADE bilan bog'langani uchun ular ham birga ketardi.

Bu testlar shu chegarani qo'riqlaydi: qoralamani o'chirsa bo'ladi, ishga
tushgan taklifnomani esa yo'q.
"""
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from taklif.models import RSVP, Mehmon, Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat
from taklif.views import SESSIYA_KALITI


@override_settings(ALLOWED_HOSTS=["testserver"])
class EskisiniOchirishTest(TestCase):
    ISM = "Dilnoza"
    SLUG = "dilnoza"

    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    # ---------- yordamchilar ----------

    def _eski_yarat(self, tolangan=False):
        eski = Taklifnoma.objects.create(
            slug=self.SLUG,
            ism_1=self.ISM,
            shablon=self.shablon,
            sana=timezone.now(),
            faol=True,
            tolangan=tolangan,
        )
        sessiya = self.client.session
        sessiya[SESSIYA_KALITI] = [eski.slug]
        sessiya.save()
        return eski

    def _yubor(self, harakat):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        maydonlar["ism_1"] = self.ISM
        maydonlar["eski_taklifnoma_harakati"] = harakat
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    # ---------- o'chirishga RUXSAT ----------

    def test_qoralama_yangilanganda_ochiriladi(self):
        """To'lanmagan, mehmonsiz, javobsiz — bu haqiqiy qoralama."""
        eski = self._eski_yarat()
        javob = self._yubor("yangilash")

        self.assertEqual(javob.status_code, 302)
        self.assertFalse(Taklifnoma.objects.filter(pk=eski.pk).exists())
        # Yangisi xuddi o'sha toza havolani oldi.
        yangi = Taklifnoma.objects.get(slug=self.SLUG)
        self.assertNotEqual(yangi.pk, eski.pk)

    # ---------- o'chirish TAQIQLANGAN ----------

    def test_tolangan_taklifnoma_ochirilmaydi(self):
        eski = self._eski_yarat(tolangan=True)
        javob = self._yubor("yangilash")

        self.assertEqual(javob.status_code, 200)  # redirect yo'q — savol qaytadi
        self.assertTrue(Taklifnoma.objects.filter(pk=eski.pk).exists())
        self.assertEqual(Taklifnoma.objects.count(), 1)  # yangisi ham yaratilmadi

    def test_javoblari_bor_taklifnoma_ochirilmaydi(self):
        """To'lanmagan bo'lsa ham: havola tarqalib, mehmonlar javob
        yozib ulgurgan bo'lishi mumkin."""
        eski = self._eski_yarat()
        RSVP.objects.create(taklifnoma=eski, ism="Aziz", keladi=True)

        self._yubor("yangilash")

        self.assertTrue(Taklifnoma.objects.filter(pk=eski.pk).exists())
        self.assertEqual(RSVP.objects.count(), 1)

    def test_mehmonlari_bor_taklifnoma_ochirilmaydi(self):
        """Shaxsiy havolalar tayyorlangan — ular tarqatilgan bo'lishi mumkin."""
        eski = self._eski_yarat()
        Mehmon.objects.create(taklifnoma=eski, ism="Aziz oila")

        self._yubor("yangilash")

        self.assertTrue(Taklifnoma.objects.filter(pk=eski.pk).exists())
        self.assertEqual(Mehmon.objects.count(), 1)

    # ---------- mijoz nimani ko'radi ----------

    def test_ochirib_bolmasa_yangilash_tugmasi_korsatilmaydi(self):
        """Bosib bo'lmaydigan tugmani ko'rsatish — mijozni aldash.
        Bunday holatda faqat "alohida saqlash" taklif qilinadi."""
        self._eski_yarat(tolangan=True)
        javob = self._yubor("yangilash")

        self.assertNotContains(javob, 'value="yangilash"')
        self.assertContains(javob, 'value="alohida"')

    def test_qoralamada_ikkala_tugma_ham_korinadi(self):
        self._eski_yarat()
        # Harakat tanlanmagan holat: savol birinchi marta ko'rsatiladi.
        javob = self._yubor("")

        self.assertContains(javob, 'value="yangilash"')
        self.assertContains(javob, 'value="alohida"')

    # ---------- alohida saqlash ----------

    def test_tolangan_bolsa_alohida_saqlash_ishlaydi(self):
        """Yagona qolgan yo'l ishlashi shart — aks holda mijoz umuman
        yangi taklifnoma yarata olmay qoladi."""
        eski = self._eski_yarat(tolangan=True)
        javob = self._yubor("alohida")

        self.assertEqual(javob.status_code, 302)
        self.assertTrue(Taklifnoma.objects.filter(pk=eski.pk).exists())
        yangi = Taklifnoma.objects.exclude(pk=eski.pk).get()
        self.assertNotEqual(yangi.slug, eski.slug)
