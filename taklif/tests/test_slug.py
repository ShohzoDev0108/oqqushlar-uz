"""_asosiy_slug / _bosh_slug_top / _band_emasligini_tekshir uchun testlar.

Bu funksiyalar mijoz ko'rmaydigan, lekin juda muhim mantiqni bajaradi:
ism_1/ism_2'dan toza (raqamsiz) havola yasash va to'qnashuvlarni orqa
fondan, mijozga bildirmasdan hal qilish.
"""
from django.test import TestCase
from django.utils import timezone

from taklif.models import Taklifnoma
from taklif.tests.yordamchi import shablon_yarat
from taklif.views import _asosiy_slug, _band_emasligini_tekshir, _bosh_slug_top


class AsosiySlugTest(TestCase):
    def test_ikki_ism_birlashtiriladi(self):
        self.assertEqual(_asosiy_slug("Sardor", "Malika"), "sardor-malika")

    def test_faqat_bitta_ism(self):
        self.assertEqual(_asosiy_slug("Aziz", ""), "aziz")

    def test_uzun_ismlar_kesiladi(self):
        uzun_ism = "a" * 200
        slug = _asosiy_slug(uzun_ism, "")
        self.assertLessEqual(len(slug), 50)  # SlugField max_length

    def test_bosh_qiymat_zaxira_soz(self):
        self.assertEqual(_asosiy_slug("", ""), "taklifnoma")


class BoshSlugTopTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()

    def test_band_bolmasa_asosiyni_qaytaradi(self):
        self.assertEqual(_bosh_slug_top("erkin-slug"), "erkin-slug")

    def test_band_bolsa_mazmunli_soz_bilan_ajratadi(self):
        Taklifnoma.objects.create(
            slug="sardor-malika", ism_1="Sardor", ism_2="Malika",
            shablon=self.shablon, sana=timezone.now(),
        )
        yangi = _bosh_slug_top("sardor-malika")
        self.assertNotEqual(yangi, "sardor-malika")
        # Hech qachon xunuk "-2" qo'shilmasligi kerak
        self.assertNotRegex(yangi, r"-\d+$")
        self.assertFalse(Taklifnoma.objects.filter(slug=yangi).exists())

    def test_band_emasligini_tekshir_rezerv_sozni_rad_etadi(self):
        self.assertFalse(_band_emasligini_tekshir("admin", chetlanganlar=()))
        self.assertFalse(_band_emasligini_tekshir("statistika", chetlanganlar=()))
