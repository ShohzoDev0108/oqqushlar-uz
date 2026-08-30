"""TelegramXatolikHandler uchun testlar — production'da 500-server-xatolik
yuz berganda Telegram botga avtomatik xabar yuborish (taftish bo'yicha
qo'shilgan xatolik-kuzatish funksiyasi)."""
import sys
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from taklif.xatolik_xabarnomasi import TelegramXatolikHandler


def _log_yozuvi_yasash(xabar="Sinov xatoligi", exc_info=None):
    import logging

    return logging.LogRecord(
        name="django.request",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg=xabar,
        args=(),
        exc_info=exc_info,
    )


class TelegramXatolikHandlerTest(SimpleTestCase):
    def setUp(self):
        self.handler = TelegramXatolikHandler()

    @override_settings(TELEGRAM_XATOLIK_BOT_TOKEN="", TELEGRAM_XATOLIK_CHAT_ID="")
    def test_sozlanmagan_bolsa_hech_narsa_yubormaydi(self):
        with patch("taklif.xatolik_xabarnomasi.urllib.request.urlopen") as urlopen:
            natija = self.handler.emit(_log_yozuvi_yasash())
        self.assertIsNone(natija)  # fon oqim umuman ishga tushmadi
        urlopen.assert_not_called()

    @override_settings(TELEGRAM_XATOLIK_BOT_TOKEN="123:ABC", TELEGRAM_XATOLIK_CHAT_ID="999")
    def test_sozlangan_bolsa_telegram_apiga_sorov_yuboradi(self):
        with patch("taklif.xatolik_xabarnomasi.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = b"{}"
            oqim = self.handler.emit(_log_yozuvi_yasash("Test xato matni"))
            self.assertIsNotNone(oqim)
            oqim.join(timeout=2)

        urlopen.assert_called_once()
        so_rov = urlopen.call_args[0][0]
        self.assertIn("123:ABC", so_rov.full_url)
        self.assertIn(b"Test xato matni", so_rov.data)

    @override_settings(TELEGRAM_XATOLIK_BOT_TOKEN="123:ABC", TELEGRAM_XATOLIK_CHAT_ID="999")
    def test_tarmoq_xatosi_boshqa_xatolikka_sabab_bolmaydi(self):
        with patch(
            "taklif.xatolik_xabarnomasi.urllib.request.urlopen",
            side_effect=OSError("ulanmadi"),
        ):
            # Bu chaqiruv hech qanday xato ko'tarmasligi kerak.
            oqim = self.handler.emit(_log_yozuvi_yasash())
            self.assertIsNotNone(oqim)
            oqim.join(timeout=2)  # ichkarida xato "yutiladi", tashqariga chiqmaydi

    def test_uzun_xabar_qisqartiriladi(self):
        try:
            raise ValueError("x" * 5000)
        except ValueError:
            exc_info = sys.exc_info()
        matn = self.handler._xabar_matni(_log_yozuvi_yasash("Uzun", exc_info=exc_info))
        self.assertLessEqual(len(matn), 3600)
        self.assertIn("qisqartirildi", matn)

    def test_request_manzili_xabarga_qoshiladi(self):
        request = MagicMock()
        request.method = "GET"
        request.get_full_path.return_value = "/yomon-sahifa/"
        record = _log_yozuvi_yasash("500 xato")
        record.request = request
        matn = self.handler._xabar_matni(record)
        self.assertIn("GET /yomon-sahifa/", matn)

    def test_html_belgilar_qochiriladi(self):
        try:
            raise ValueError("<script>alert(1)</script>")
        except ValueError:
            exc_info = sys.exc_info()
        matn = self.handler._xabar_matni(_log_yozuvi_yasash("XSS sinovi", exc_info=exc_info))
        self.assertNotIn("<script>", matn)
        self.assertIn("&lt;script&gt;", matn)
