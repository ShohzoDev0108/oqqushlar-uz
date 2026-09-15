"""Yuklangan rasmlarni optimallashtirish.

TAFTISH TOPILMASI. Rasm mijoz yuklagan holida saqlanardi — 4000x3000
piksel, 6-8 MB. Har bir mehmon taklifnomani ochganda shuncha yuklab
olardi, ko'pincha mobil internetdan. Bu sekinlik, mehmonning trafigi
va R2 hisobidagi pul edi.

Uchinchi test guruhi eng muhimi: telefon fotosi ichida GPS KOORDINATASI
bo'ladi, taklifnoma sahifasi esa havolani bilgan har kimga ochiq. Ya'ni
mijozning uyida olingan foto bilan birga uy manzili ham ommaga chiqib
ketardi.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from taklif.models import NamunaRasm, TaklifnomaRasm, Taklifnoma
from taklif.rasm import MAKS_TOMON, NAMUNA_MAKS_TOMON, optimallashtir
from taklif.tests.yordamchi import shablon_yarat


def _rasm_baytlari(kenglik, balandlik, format="JPEG", exif=None):
    from PIL import Image

    buffer = io.BytesIO()
    rasm = Image.new("RGB", (kenglik, balandlik), color=(200, 120, 60))
    if exif is not None:
        rasm.save(buffer, format=format, exif=exif)
    else:
        rasm.save(buffer, format=format)
    return buffer.getvalue()


def _yuklangan(nom="foto.jpg", kenglik=3000, balandlik=2000, **kw):
    return SimpleUploadedFile(
        nom, _rasm_baytlari(kenglik, balandlik, **kw), content_type="image/jpeg"
    )


class OptimallashtirishTest(TestCase):
    def test_katta_rasm_kichraytiriladi(self):
        natija = optimallashtir(_yuklangan(kenglik=4000, balandlik=3000))
        from PIL import Image

        rasm = Image.open(io.BytesIO(natija.read()))
        self.assertEqual(max(rasm.size), MAKS_TOMON)

    def test_kichik_rasm_kattalashtirilmaydi(self):
        """Kichik rasmni cho'zish sifatni buzadi va faylni og'irlashtiradi."""
        natija = optimallashtir(_yuklangan(kenglik=400, balandlik=300))
        from PIL import Image

        rasm = Image.open(io.BytesIO(natija.read()))
        self.assertEqual(rasm.size, (400, 300))

    def test_webp_ga_ogiriladi(self):
        natija = optimallashtir(_yuklangan("Mening Fotom.jpg"))
        self.assertTrue(natija.name.endswith(".webp"), natija.name)
        from PIL import Image

        self.assertEqual(Image.open(io.BytesIO(natija.read())).format, "WEBP")

    def test_hajm_sezilarli_kichrayadi(self):
        asl = _yuklangan(kenglik=4000, balandlik=3000)
        asl_hajm = len(asl.read())
        natija = optimallashtir(asl)
        self.assertLess(len(natija.read()), asl_hajm)

    def test_buzuq_fayl_sorovni_qulatmaydi(self):
        """`optimallashtir()`ning o'zi buzuq fayl uchun istisno (exception)
        ko'tarmasligi kerak — sof funksiya sifatida jimgina None qaytaradi.

        DIQQAT (2026-09-14 yangilandi): bu "None qaytarish" endi so'rovni
        MUVAFFAQIYATLI davom ettirish degani EMAS — chaqiruvchi tomon
        (`_rasmni_optimallashtirib_saqlash`, models.py) buni RasmXatosi
        sifatida ko'taradi, `taklif/views.py`dagi yaratish oqimi esa bunday
        faylni taklifnoma yaratilishidan OLDIN rad etadi (qarang:
        test_yaratish.py -> test_buzuq_rasm_rad_etiladi_va_hech_narsa_saqlanmaydi).
        Bu test faqat quyi darajadagi funksiyaning o'zi qulamasligini
        tekshiradi."""
        buzuq = SimpleUploadedFile("buzuq.jpg", b"bu rasm emas", content_type="image/jpeg")
        self.assertIsNone(optimallashtir(buzuq))

    def test_piksel_chegarasidan_katta_rasm_rad_etiladi(self):
        """"Dekompressiya bombasi"dan himoya (MAKS_PIKSEL — rasm.py).

        Haqiqiy bombani sinovda hosil qilish (masalan o'n minglab x o'n
        minglab piksel) test muhitida ham xotira sarflaydi — shuning uchun
        chegaraning o'zini vaqtincha pasaytirib, oddiy kichik rasm bilan
        tekshiramiz.
        """
        from unittest.mock import patch

        with patch("taklif.rasm.MAKS_PIKSEL", 100):
            natija = optimallashtir(_yuklangan(kenglik=400, balandlik=300))
        self.assertIsNone(natija)


class ExifMaxfiyligiTest(TestCase):
    """GPS koordinatasi ommaga chiqib ketmasligi kerak."""

    def test_metamalumot_saqlanmaydi(self):
        from PIL import Image

        # Pillow'ning o'z EXIF obyekti orqali "qurilma nomi"ni yozamiz —
        # GPS ham xuddi shu mexanizm bilan saqlanadi.
        exif = Image.Exif()
        exif[271] = "SinovTelefon"  # Make
        exif[272] = "Model-X"       # Model
        baytlar = _rasm_baytlari(800, 600, exif=exif)
        asl = SimpleUploadedFile("gps.jpg", baytlar, content_type="image/jpeg")

        # Asl faylda metama'lumot BOR ekanini avval tasdiqlaymiz — aks
        # holda test hech narsani isbotlamagan bo'lardi.
        self.assertIn(b"SinovTelefon", baytlar)

        natija = optimallashtir(asl)
        yangi_baytlar = natija.read()
        self.assertNotIn(b"SinovTelefon", yangi_baytlar)
        self.assertNotIn(b"Model-X", yangi_baytlar)


@override_settings(MEDIA_ROOT="/tmp/oqqushlar-rasm-test")
class ModelSaqlashTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()
        self.taklifnoma = Taklifnoma.objects.create(
            slug="rasm-sinovi", ism_1="Mezbon", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )

    def test_taklifnoma_rasmi_webp_bolib_saqlanadi(self):
        obyekt = TaklifnomaRasm.objects.create(
            taklifnoma=self.taklifnoma, rasm=_yuklangan()
        )
        self.assertTrue(obyekt.rasm.name.endswith(".webp"), obyekt.rasm.name)

    def test_namuna_rasm_kichikroq_olchamda(self):
        """Namunalar formada bir nechtasi birdan ko'rsatiladi — ular
        yig'ilib og'irlik qiladi."""
        obyekt = NamunaRasm.objects.create(rasm=_yuklangan(kenglik=3000, balandlik=2000))
        from PIL import Image

        obyekt.rasm.open("rb")
        rasm = Image.open(io.BytesIO(obyekt.rasm.read()))
        obyekt.rasm.close()
        self.assertEqual(max(rasm.size), NAMUNA_MAKS_TOMON)

    def test_qayta_saqlash_faylni_ozgartirmaydi(self):
        """Har save()'da qayta siqish sifatni asta-sekin yeb qo'yardi."""
        obyekt = TaklifnomaRasm.objects.create(
            taklifnoma=self.taklifnoma, rasm=_yuklangan()
        )
        birinchi_nom = obyekt.rasm.name

        obyekt.tartib = 5
        obyekt.save()

        self.assertEqual(obyekt.rasm.name, birinchi_nom)

    def test_buzuq_rasm_saqlanmaydi(self):
        """TAFTISH TOPILMASI (2026-09-14): ilgari buzuq fayl optimallashmay
        qolsa ham, ASL (EXIF/GPS'li) fayl bilan baribir saqlanardi. Endi
        umuman saqlanmaydi — RasmXatosi ko'tariladi."""
        from taklif.rasm import RasmXatosi

        with self.assertRaises(RasmXatosi):
            TaklifnomaRasm.objects.create(
                taklifnoma=self.taklifnoma,
                rasm=SimpleUploadedFile(
                    "buzuq.jpg", b"bu rasm emas", content_type="image/jpeg"
                ),
            )
        self.assertEqual(self.taklifnoma.rasmlar.count(), 0)
