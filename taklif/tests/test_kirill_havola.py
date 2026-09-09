"""Kirillda yozilgan ismlardan havola yasash.

TAFTISH TOPILMASI. Django'ning slugify() funksiyasi lotin bo'lmagan
harflarni tashlab yuboradi, ya'ni slugify("Шоҳзод") -> "". Natijada
kirillda yozgan har bir mijoz "taklifnoma", "taklifnoma-20-05",
"taklifnoma-toy" kabi havola olardi — mahsulotning butun g'oyasi esa
"sayt.uz/sardor-malika" kabi chiroyli havola berish edi.

O'zbekistonda kirillda yozish keng tarqalgan, ya'ni bu chekka holat emas.
"""
from django.test import Client, TestCase, override_settings

from taklif.models import Mehmon, Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat
from taklif.translit import kirilldan_lotinga


class TranslitTest(TestCase):
    def test_ozbek_kirillchasi_ogiriladi(self):
        self.assertEqual(kirilldan_lotinga("Шоҳзод"), "shohzod")
        self.assertEqual(kirilldan_lotinga("Ўғилой"), "ogiloy")
        self.assertEqual(kirilldan_lotinga("Ҳусан"), "husan")

    def test_rus_qozoq_va_tojik_harflari(self):
        self.assertEqual(kirilldan_lotinga("Алексей"), "aleksey")
        self.assertEqual(kirilldan_lotinga("Айгүл"), "aygul")
        self.assertEqual(kirilldan_lotinga("Ҷамшед"), "jamshed")

    def test_ayirish_belgisi_keyingi_unlini_buzmaydi(self):
        self.assertEqual(kirilldan_lotinga("Подъезд"), "podezd")

    def test_lotin_matni_ozgarmaydi(self):
        """Funksiya har doim chaqiriladi — lotin matnni buzmasligi shart."""
        self.assertEqual(kirilldan_lotinga("Sardor-Malika"), "sardor-malika")

    def test_bosh_qiymatlar(self):
        self.assertEqual(kirilldan_lotinga(""), "")
        self.assertEqual(kirilldan_lotinga(None), "")


@override_settings(ALLOWED_HOSTS=["testserver"])
class KirillTaklifnomaTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    def _post(self, qoshimcha):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        maydonlar.update(qoshimcha)
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    def test_kirill_ismdan_mazmunli_havola_chiqadi(self):
        self._post({"marosim_turi": "toy", "ism_1": "Сардор", "ism_2": "Малика"})
        taklifnoma = Taklifnoma.objects.get(ism_1="Сардор")
        self.assertEqual(taklifnoma.slug, "sardor-malika")

    def test_ikki_xil_kirill_ism_toqnashmaydi(self):
        """Ilgari ikkalasi ham "taklifnoma" ga tushib, ikkinchisiga
        ma'nosiz qo'shimcha yopishtirilardi."""
        self._post({"ism_1": "Шоҳзод"})
        Client().post(  # boshqa mijoz, boshqa sessiya
            f"/yaratish/{self.shablon.kod}/",
            dict(ASOSIY_FORMA_MAYDONLARI, ism_1="Дилноза"),
        )
        sluglar = set(Taklifnoma.objects.values_list("slug", flat=True))
        self.assertEqual(sluglar, {"shohzod", "dilnoza"})

    def test_kirill_havola_ochiladi(self):
        self._post({"ism_1": "Шоҳзод"})
        taklifnoma = Taklifnoma.objects.get(ism_1="Шоҳзод")
        taklifnoma.tolangan = True
        taklifnoma.save(update_fields=["tolangan"])

        javob = Client().get(f"/{taklifnoma.slug}/")
        self.assertEqual(javob.status_code, 200)


class KirillMehmonTest(TestCase):
    """Mehmon o'z ismini ko'rishi kerak, "mehmon-3" ni emas."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="kirill-mehmon", ism_1="Mezbon", shablon=self.shablon,
            sana="2027-05-20T18:00", faol=True, tolangan=True,
        )

    def test_kirill_mehmon_ismidan_havola(self):
        mehmon = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Азиз оила")
        self.assertEqual(mehmon.slug, "aziz-oila")

    def test_ikki_kirill_mehmon_raqamsiz_ajratiladi(self):
        birinchi = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Азиз")
        ikkinchi = Mehmon.objects.create(taklifnoma=self.taklifnoma, ism="Дилshod")
        self.assertEqual(birinchi.slug, "aziz")
        self.assertEqual(ikkinchi.slug, "dilshod")
