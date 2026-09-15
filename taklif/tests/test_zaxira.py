# -*- coding: utf-8 -*-
"""Zaxira nusxa buyrug'i.

Bu testlar R2'ga ham, PostgreSQL'ga ham ulanmaydi — ular buyruqning
QAROR qabul qiladigan qismlarini tekshiradi: sozlamalar noto'g'ri
bo'lsa to'xtatadimi, va qaysi nusxani saqlab, qaysinisini o'chiradi.

Eng muhim testlar — birinchi ikkitasi. Ular "zaxira bor" degan yolg'on
xotirjamlikning oldini oladi: paqir media bilan bir xil bo'lsa yoki
parol yo'q bo'lsa, buyruq jimgina ishlashi MUMKIN EMAS.
"""
import datetime
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from taklif.management.commands.zaxira import (
    Command,
    HAFTALIK_SAQLASH_KUNI,
    HAJM_PASAYISH_CHEGARASI,
    KUNDALIK_SAQLASH_KUNI,
    NOM_NAQSHI,
    saqlanadimi,
)


class SozlamaTekshiruviTest(SimpleTestCase):
    """Noto'g'ri sozlama bilan buyruq ishlamasligi kerak."""

    @override_settings(ZAXIRA_BUCKET="", ZAXIRA_PAROL="juda-uzun-parol-shu-yerda-turadi")
    def test_paqir_korsatilmagan_bolsa_toxtaydi(self):
        with self.assertRaises(CommandError) as qutqargich:
            call_command("zaxira", "--sinov")
        self.assertIn("ZAXIRA_BUCKET", str(qutqargich.exception))

    @override_settings(ZAXIRA_BUCKET="oqqushlar-zaxira", ZAXIRA_PAROL="")
    def test_parol_yoq_bolsa_toxtaydi(self):
        """Bazada mijozlar va mehmonlarning shaxsiy ma'lumoti bor —
        shifrsiz nusxa olish taklif ham qilinmasligi kerak."""
        with self.assertRaises(CommandError) as qutqargich:
            call_command("zaxira", "--sinov")
        self.assertIn("ZAXIRA_PAROL", str(qutqargich.exception))

    @override_settings(ZAXIRA_BUCKET="oqqushlar-zaxira", ZAXIRA_PAROL="qisqa")
    def test_qisqa_parol_qabul_qilinmaydi(self):
        with self.assertRaises(CommandError):
            call_command("zaxira", "--sinov")

    @override_settings(
        ZAXIRA_BUCKET="oqqushlar-media",
        AWS_STORAGE_BUCKET_NAME="oqqushlar-media",
        ZAXIRA_PAROL="juda-uzun-parol-shu-yerda-turadi",
    )
    def test_media_paqiri_bilan_bir_xil_bolsa_toxtaydi(self):
        """Eng muhim himoya: zaxira media bilan bir paqirda turmasin.
        Aks holda bitta noto'g'ri kalit ikkalasini birdan yo'q qiladi."""
        with self.assertRaises(CommandError) as qutqargich:
            call_command("zaxira", "--sinov")
        self.assertIn("alohida", str(qutqargich.exception).lower())


class SaqlashMuddatiTest(SimpleTestCase):
    """Qaysi nusxa qoladi, qaysinisi o'chadi."""

    BUGUN = datetime.date(2026, 9, 9)  # chorshanba

    def test_oxirgi_ikki_hafta_hammasi_qoladi(self):
        for yosh in (0, 1, 7, KUNDALIK_SAQLASH_KUNI):
            sana = self.BUGUN - datetime.timedelta(days=yosh)
            self.assertTrue(saqlanadimi(sana, self.BUGUN), f"{yosh} kunlik nusxa")

    def test_ikki_haftadan_keyin_faqat_yakshanba_qoladi(self):
        # 2026-08-16 yakshanba, 2026-08-17 dushanba — ikkalasi ham 14 kundan eski
        yakshanba = datetime.date(2026, 8, 16)
        dushanba = datetime.date(2026, 8, 17)
        self.assertEqual(yakshanba.weekday(), 6)
        self.assertTrue(saqlanadimi(yakshanba, self.BUGUN))
        self.assertFalse(saqlanadimi(dushanba, self.BUGUN))

    def test_juda_eski_nusxa_yakshanba_bolsa_ham_ochadi(self):
        eski = self.BUGUN - datetime.timedelta(days=HAFTALIK_SAQLASH_KUNI + 7)
        while eski.weekday() != 6:
            eski -= datetime.timedelta(days=1)
        self.assertFalse(saqlanadimi(eski, self.BUGUN))

    def test_chegara_kuni_hali_saqlanadi(self):
        """Chegara qat'iy bo'lsa, kunning oxirida kutilmaganda nusxa
        yo'qolib qolishi mumkin — shuning uchun chegara kuni ham qoladi."""
        sana = self.BUGUN - datetime.timedelta(days=KUNDALIK_SAQLASH_KUNI)
        self.assertTrue(saqlanadimi(sana, self.BUGUN))


class HajmPasayishiTest(SimpleTestCase):
    """TAFTISH TOPILMASI (2026-09-14): yangi nusxa oldingi eng so'nggisidan
    shubhali darajada kichraysa, admin xabardor bo'lishi kerak (lekin
    zaxira olish to'xtatilmaydi — sabab: docstring, zaxira.py)."""

    def setUp(self):
        self.buyruq = Command()

    def test_oldingi_nusxa_bolmasa_hech_narsa_qilinmaydi(self):
        with self.assertNoLogs("taklif.zaxira", level="ERROR"):
            self.buyruq._hajm_pasayishini_tekshir(100, [])

    def test_kichik_pasayish_ogohlantirmaydi(self):
        # 90% — chegaradan (50%) yuqori, oddiy tebranish.
        oldingi = [("k", datetime.date(2026, 9, 1), 1000)]
        with self.assertNoLogs("taklif.zaxira", level="ERROR"):
            self.buyruq._hajm_pasayishini_tekshir(900, oldingi)

    def test_shubhali_pasayish_ogohlantiradi(self):
        oldingi = [("k", datetime.date(2026, 9, 1), 1000)]
        yangi_hajm = int(1000 * HAJM_PASAYISH_CHEGARASI) - 1
        with self.assertLogs("taklif.zaxira", level="ERROR") as jurnal:
            self.buyruq._hajm_pasayishini_tekshir(yangi_hajm, oldingi)
        self.assertTrue(any("shubhali" in x for x in jurnal.output))


class YuborishTekshiruviTest(SimpleTestCase):
    """TAFTISH TOPILMASI (2026-09-14): hajm mos kelmasa (nomos yuklama),
    R2'da qolib ketmasligi kerak — o'chirishga urinilishi shart."""

    def test_hajm_mos_kelmasa_nomos_fayl_ochiriladi(self):
        buyruq = Command()
        soxta_mijoz = MagicMock()
        soxta_mijoz.head_object.return_value = {"ContentLength": 5}

        with patch.object(Command, "_mijoz", return_value=soxta_mijoz), \
             patch("builtins.open", MagicMock()):
            with self.assertRaises(CommandError):
                buyruq._yuborish("paqir", "nom.gpg", "/soxta/yol", 999)

        soxta_mijoz.delete_object.assert_called_once_with(
            Bucket="paqir", Key="nom.gpg"
        )


class FaylNomiTest(SimpleTestCase):
    """Sana fayl NOMIDAN o'qiladi — R2'ning o'z vaqtiga tayanilmaydi,
    chunki nusxa ko'chirilganda u yangilanib ketadi."""

    def test_togri_nom_tanilib_olinadi(self):
        moslik = NOM_NAQSHI.match("zaxira/oqqushlar-2026-09-09-0300.dump.gpg")
        self.assertIsNotNone(moslik)
        self.assertEqual(moslik.groups(), ("2026", "09", "09"))

    def test_begona_fayllar_royxatga_tushmaydi(self):
        for nom in (
            "zaxira/boshqa-fayl.txt",
            "media/rasm.jpg",
            "zaxira/oqqushlar-2026-09-09.dump.gpg",   # vaqtsiz
            "zaxira/oqqushlar-2026-09-09-0300.dump",  # shifrlanmagan
        ):
            self.assertIsNone(NOM_NAQSHI.match(nom), nom)
