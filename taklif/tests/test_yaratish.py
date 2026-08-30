"""Mijoz o'zi taklifnoma yaratish oqimi (self-service) uchun testlar."""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from taklif.models import MUSIQA_MAKS_HAJM_MB, RASM_MAKS_HAJM_MB, Taklifnoma
from taklif.tests.yordamchi import ASOSIY_FORMA_MAYDONLARI, shablon_yarat
from taklif.views import SESSIYA_KALITI


def _kichik_jpeg_baytlari():
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover
        return b"\xff\xd8\xff\xe0" + b"\x00" * 100  # to'liq to'g'ri JPEG bo'lmasa ham yetarli emas
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buf, format="JPEG")
    return buf.getvalue()


@override_settings(ALLOWED_HOSTS=["testserver"])
class TaklifnomaYaratishTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    def _post(self, qoshimcha=None, files=None):
        maydonlar = dict(ASOSIY_FORMA_MAYDONLARI)
        if qoshimcha:
            maydonlar.update(qoshimcha)
        if files:
            maydonlar.update(files)
        return self.client.post(f"/yaratish/{self.shablon.kod}/", maydonlar)

    def test_togri_malumot_bilan_yaratiladi(self):
        r = self._post({"ism_1": "Bitmas"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Taklifnoma.objects.filter(ism_1="Bitmas").exists())

    def test_yangi_taklifnoma_tolanmagan_va_faol(self):
        self._post({"ism_1": "Yangi"})
        t = Taklifnoma.objects.get(ism_1="Yangi")
        self.assertFalse(t.tolangan)
        self.assertTrue(t.faol)

    def test_sessiyaga_qoshiladi(self):
        self._post({"ism_1": "Sessiyada"})
        t = Taklifnoma.objects.get(ism_1="Sessiyada")
        self.assertIn(t.slug, self.client.session.get(SESSIYA_KALITI, []))

    def test_ikki_ismli_marosim_uchun_ism_2_shart(self):
        r = self._post({"marosim_turi": "toy", "ism_1": "Kuyov", "ism_2": ""})
        self.assertEqual(r.status_code, 200)  # forma xatosi bilan qaytadi, redirect emas
        self.assertFalse(Taklifnoma.objects.filter(ism_1="Kuyov").exists())

    def test_ommaviy_korsatish_belgisi_qoyilmasa_standart_holatda_ochiq_emas(self):
        # Taftish topilmasi: bosh sahifada mijoz roziligisiz ism/sana
        # ko'rsatilmasligi kerak — shuning uchun checkbox POST qilinmasa
        # (brauzer belgilanmagan checkbox'ni umuman yubormaydi), standart
        # holat albatta False bo'lishi kerak.
        self._post({"ism_1": "Roziliksiz"})
        t = Taklifnoma.objects.get(ism_1="Roziliksiz")
        self.assertFalse(t.ommaviy_korsatishga_rozi)

    def test_ommaviy_korsatish_belgisi_qoyilsa_saqlanadi(self):
        self._post({"ism_1": "Rozi", "ommaviy_korsatishga_rozi": "on"})
        t = Taklifnoma.objects.get(ism_1="Rozi")
        self.assertTrue(t.ommaviy_korsatishga_rozi)

    def test_boshqa_mijoz_bir_xil_ism_yozsa_raqamsiz_ajratiladi(self):
        # Birinchi mijoz (boshqa sessiya) "Aziz" nomli taklifnoma yaratadi.
        Client().post(f"/yaratish/{self.shablon.kod}/", {**ASOSIY_FORMA_MAYDONLARI, "ism_1": "Aziz"})
        # Ikkinchi (joriy) mijoz ham "Aziz" deb yozadi — bu UNING o'zi yaratgani emas.
        r = self._post({"ism_1": "Aziz"})
        self.assertEqual(r.status_code, 302)
        ikkinchisi = Taklifnoma.objects.filter(ism_1="Aziz").exclude(slug="aziz").first()
        self.assertIsNotNone(ikkinchisi)
        # Xunuk, mazmunsiz ketma-ket hisoblagich ("aziz-2", "aziz-3") EMAS —
        # sana/marosim/so'z kabi mazmunli qo'shimcha bo'lishi kerak (bular
        # tabiiy ravishda ham raqam bilan tugashi mumkin, masalan sana-oy —
        # shu uchun "faqat bitta-ikkita raqam" emas, aynan hisoblagich
        # naqshini tekshiramiz).
        self.assertNotRegex(ikkinchisi.slug, r"^aziz-\d{1,2}$")


@override_settings(ALLOWED_HOSTS=["testserver"])
class FaylCheklovlariTest(TestCase):
    """Fayl yuklashda tur/hajm cheklovlari (audit topilmasi — tuzatilgan)."""

    def setUp(self):
        self.shablon = shablon_yarat()
        self.client = Client()

    def _post(self, **files):
        return self.client.post(
            f"/yaratish/{self.shablon.kod}/", {**ASOSIY_FORMA_MAYDONLARI, **files}
        )

    def test_notogri_kengaytmali_musiqa_rad_etiladi(self):
        r = self._post(musiqa=SimpleUploadedFile("zararli.exe", b"MZ", content_type="application/octet-stream"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Taklifnoma.objects.exists())

    def test_juda_katta_musiqa_rad_etiladi(self):
        katta = b"x" * (MUSIQA_MAKS_HAJM_MB * 1024 * 1024 + 1)
        r = self._post(musiqa=SimpleUploadedFile("katta.mp3", katta, content_type="audio/mpeg"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Taklifnoma.objects.exists())

    def test_togri_musiqa_qabul_qilinadi(self):
        r = self._post(musiqa=SimpleUploadedFile("ok.mp3", b"ID3" + b"x" * 100, content_type="audio/mpeg"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Taklifnoma.objects.exists())

    def test_juda_katta_rasm_rad_etiladi_va_hech_narsa_saqlanmaydi(self):
        katta_rasm = b"\xff\xd8\xff" + b"x" * (RASM_MAKS_HAJM_MB * 1024 * 1024 + 1)
        r = self.client.post(
            f"/yaratish/{self.shablon.kod}/",
            {**ASOSIY_FORMA_MAYDONLARI, "rasmlar": [SimpleUploadedFile("katta.jpg", katta_rasm, "image/jpeg")]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Taklifnoma.objects.exists())  # chala taklifnoma qolib ketmasligi kerak

    def test_togri_hajmdagi_rasm_biriktiriladi(self):
        r = self.client.post(
            f"/yaratish/{self.shablon.kod}/",
            {**ASOSIY_FORMA_MAYDONLARI, "rasmlar": [SimpleUploadedFile("ok.jpg", _kichik_jpeg_baytlari(), "image/jpeg")]},
        )
        self.assertEqual(r.status_code, 302)
        t = Taklifnoma.objects.first()
        self.assertIsNotNone(t)
        self.assertEqual(t.rasmlar.count(), 1)


@override_settings(ALLOWED_HOSTS=["testserver"])
class NamunaRasmKosmetikTest(TestCase):
    """Taftish topilmasi: namuna-rasm tanlash to'ridagi <img>'lar bo'sh
    alt="" bilan chiqar edi (skrin-o'quvchi uchun mazmunsiz) va JS massivi
    Python ro'yxatini |safe bilan to'g'ridan-to'g'ri qo'yardi (maxsus
    belgilar bo'lsa xavfli). Ikkalasi ham tuzatilgan."""

    def setUp(self):
        self.shablon = shablon_yarat()

    def test_nomi_bolmagan_namuna_rasm_raqamli_alt_oladi(self):
        from taklif.models import NamunaRasm

        NamunaRasm.objects.create(
            nomi="", rasm=SimpleUploadedFile("n.jpg", _kichik_jpeg_baytlari(), "image/jpeg"), faol=True
        )
        r = Client().get(f"/yaratish/{self.shablon.kod}/")
        self.assertContains(r, 'alt="Namuna rasm 1"')

    def test_nomi_bergan_namuna_rasm_shu_nomdan_foydalanadi(self):
        from taklif.models import NamunaRasm

        NamunaRasm.objects.create(
            nomi="Bahor gullari",
            rasm=SimpleUploadedFile("n2.jpg", _kichik_jpeg_baytlari(), "image/jpeg"),
            faol=True,
        )
        r = Client().get(f"/yaratish/{self.shablon.kod}/")
        self.assertContains(r, 'alt="Bahor gullari"')

    def test_ikki_ismli_turlar_json_script_orqali_chiqadi(self):
        # |safe emas, json_script orqali — xavfsizroq va JS massivini
        # to'g'ri hosil qiladi.
        r = Client().get(f"/yaratish/{self.shablon.kod}/")
        self.assertContains(r, '<script id="ikki-ismli-turlar-data" type="application/json">')
        self.assertContains(r, '"toy"')
