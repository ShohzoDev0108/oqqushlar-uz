"""`eski_chiqindilarni_tozalash` boshqaruv buyrug'i uchun testlar."""
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from taklif.management.commands.eski_chiqindilarni_tozalash import Command
from taklif.models import CHIQINDI_SAQLASH_KUNLARI, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat


class EskiChiqindilarniTozalashTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()

    def _chiqindi_yarat(self, slug, kun_oldin):
        return Taklifnoma.objects.create(
            slug=slug, ism_1=slug, shablon=self.shablon, sana=timezone.now(),
            faol=False, tolangan=True,
            ochirilgan_vaqt=timezone.now() - timedelta(days=kun_oldin),
        )

    def test_muddati_otgan_chiqindi_ochiriladi(self):
        eski = self._chiqindi_yarat("eski-chiqindi", CHIQINDI_SAQLASH_KUNLARI + 1)
        call_command("eski_chiqindilarni_tozalash", stdout=StringIO())
        self.assertFalse(Taklifnoma.objects.filter(pk=eski.pk).exists())

    def test_muddati_otmagan_chiqindi_saqlanadi(self):
        yangi = self._chiqindi_yarat("yangi-chiqindi", 1)
        call_command("eski_chiqindilarni_tozalash", stdout=StringIO())
        self.assertTrue(Taklifnoma.objects.filter(pk=yangi.pk).exists())

    def test_ochirilmagan_taklifnoma_tegilmaydi(self):
        oddiy = Taklifnoma.objects.create(
            slug="oddiy-faol", ism_1="Oddiy", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        call_command("eski_chiqindilarni_tozalash", stdout=StringIO())
        self.assertTrue(Taklifnoma.objects.filter(pk=oddiy.pk).exists())

    def test_sinov_rejimi_hech_narsani_ochirmaydi(self):
        eski = self._chiqindi_yarat("sinov-rejimi", CHIQINDI_SAQLASH_KUNLARI + 5)
        out = StringIO()
        call_command("eski_chiqindilarni_tozalash", "--sinov", stdout=out)
        self.assertTrue(Taklifnoma.objects.filter(pk=eski.pk).exists())
        self.assertIn("SINOV", out.getvalue())


class XatolikJurnaliTest(TestCase):
    """TAFTISH TOPILMASI (2026-09-14): bu buyruq ham zaxira.py kabi
    kechasi hech kim ko'rmasdan ishlaydi — ichkarida kutilmagan xatolik
    yuz bersa, jimgina yo'qolmasdan Telegram'ga (taklif.eski_chiqindilarni_tozalash
    logeri orqali) yetib borishi kerak."""

    def test_kutilmagan_xatolik_jurnalga_yoziladi_va_commanderror_kotariladi(self):
        buyruq = Command()
        with patch.object(
            Command, "_tozala", side_effect=RuntimeError("bazaga ulanib bo'lmadi")
        ):
            with self.assertLogs(
                "taklif.eski_chiqindilarni_tozalash", level="ERROR"
            ) as jurnal:
                with self.assertRaises(CommandError):
                    buyruq.handle(sinov=False)
        self.assertTrue(any("bazaga ulanib bo'lmadi" in x for x in jurnal.output))
