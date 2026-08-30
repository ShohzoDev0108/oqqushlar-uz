"""Production'da kutilmagan xatolik (500-server-error) yuz berganda,
Django logging orqali xato haqida Telegram botga avtomatik xabar yuboradi.

Nima uchun kerak: taftish paytida aniqlandiki, production serverda hech
qanday xatolik-kuzatish (error monitoring) yo'q edi — DEBUG=False bo'lganda
Django xatoliklarni faqat ADMINS ro'yxatiga email orqali yubormoqchi bo'ladi
(standart "mail_admins" handler), lekin bu loyihada ADMINS sozlanmagan va
email yuborish umuman ishlatilmaydi. Natijada mijozlarga "Serverda xatolik
yuz berdi" sahifasi chiqsa ham, admin bundan umuman xabar topmas edi.

Bu yechim ataylab eng oddiy yo'l bilan qilingan: tashqi kutubxona (masalan
`requests` yoki `sentry-sdk`) talab qilinmaydi — faqat standart kutubxona
(`urllib`) ishlatiladi, shuning uchun serverda qo'shimcha `pip install`
shart emas, faqat ikkita muhit o'zgaruvchisini sozlash kifoya:

    TELEGRAM_XATOLIK_BOT_TOKEN — @BotFather orqali yaratilgan bot tokeni
    TELEGRAM_XATOLIK_CHAT_ID   — xabar yuboriladigan chat/kanal ID'si

Agar ular sozlanmagan bo'lsa, handler hech narsa qilmay jim turadi (na
xatolik beradi, na sekinlashtiradi) — shuning uchun mahalliy/test muhitida
xavfsiz.
"""
import json
import logging
import threading
import traceback
import urllib.error
import urllib.request

from django.conf import settings

# Telegram xabar hajmi chegarasi (haqiqiy limit 4096 belgi — xavfsizlik
# uchun ozroq zaxira bilan kesamiz).
_XABAR_UZUNLIGI_CHEGARASI = 3500

_SO_ROV_TAYMAUTI_SONIYA = 5


class TelegramXatolikHandler(logging.Handler):
    """`logging.Handler` — ERROR darajasidagi log yozuvlarini (masalan,
    Django'ning `django.request` logeri orqali kelgan 500-xatoliklarni)
    Telegram botga xabar sifatida yuboradi.

    Tarmoq so'rovi alohida (fon) oqimda (thread) bajariladi — shu tufayli
    Telegram'ga ulanish sekin bo'lsa ham, foydalanuvchiga ko'rsatilayotgan
    xatolik sahifasi kechikmaydi. Oqim ataylab DAEMON EMAS (`daemon=False`)
    qilib qo'yilgan: agar daemon bo'lganida, gunicorn workeri xatolikni
    log qilgandan darhol keyin qayta ishga tushirilsa/to'xtatilsa (masalan
    deploy paytida), Telegram'ga so'rov hali yetib bormasdan fon oqimi
    majburan o'chirilib, xabar hech qachon yetib bormasligi mumkin edi.
    """

    def emit(self, record):
        """`logging` moduli chaqiradi. Fon oqimini qaytaradi (yoki hech
        narsa yubormasa `None`) — bu qaytariladigan qiymat odatiy ishlatishda
        e'tiborga olinmaydi, faqat testlarda oqim tugashini kutish uchun
        qulay."""
        token = getattr(settings, "TELEGRAM_XATOLIK_BOT_TOKEN", "")
        chat_id = getattr(settings, "TELEGRAM_XATOLIK_CHAT_ID", "")
        if not token or not chat_id:
            return None
        try:
            matn = self._xabar_matni(record)
        except Exception:
            # Xabar matnini tuzishda kutilmagan xato chiqsa ham, bu asosiy
            # so'rov/javobga hech qanday ta'sir qilmasligi kerak.
            return None
        thread = threading.Thread(
            target=self._xavfsiz_yuborish,
            args=(token, chat_id, matn),
            daemon=False,
        )
        thread.start()
        return thread

    def _xabar_matni(self, record):
        satrlar = [
            "\U0001f534 Oqqushlar saytida xatolik",
            f"Daraja: {record.levelname}",
        ]
        request = getattr(record, "request", None)
        if request is not None:
            try:
                satrlar.append(f"Manzil: {request.method} {request.get_full_path()}")
            except Exception:
                pass
        satrlar.append(f"Xabar: {record.getMessage()}")
        if record.exc_info:
            tb = "".join(traceback.format_exception(*record.exc_info))
            satrlar.append("")
            satrlar.append(f"<pre>{self._html_qochir(tb)}</pre>")
        matn = "\n".join(satrlar)
        if len(matn) > _XABAR_UZUNLIGI_CHEGARASI:
            matn = matn[:_XABAR_UZUNLIGI_CHEGARASI] + "\n... (qisqartirildi)"
        return matn

    @staticmethod
    def _html_qochir(matn):
        return matn.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @classmethod
    def _xavfsiz_yuborish(cls, token, chat_id, matn):
        try:
            cls._yuborish(token, chat_id, matn)
        except Exception:
            # Telegram serveriga ulanib bo'lmasa (tarmoq xatosi, noto'g'ri
            # token va h.k.), bu jimgina e'tiborsiz qoldiriladi — aks holda
            # xatolik haqida xabar yuborish urinishining o'zi yangi xatolik
            # keltirib chiqarishi mumkin edi.
            pass

    @staticmethod
    def _yuborish(token, chat_id, matn):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        maydonlar = json.dumps(
            {
                "chat_id": chat_id,
                "text": matn,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")
        so_rov = urllib.request.Request(
            url,
            data=maydonlar,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(so_rov, timeout=_SO_ROV_TAYMAUTI_SONIYA) as javob:
            javob.read()
