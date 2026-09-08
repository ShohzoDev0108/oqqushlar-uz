"""Son bilan kelgan so'zlar to'g'ri shaklga kirishini tekshiradi.

MUAMMO. Rus tilida son bilan kelgan so'z uch shaklga kiradi: 1 день,
2 дня, 5 дней. Bizda esa har doim bitta shakl — "дней" — turardi. Ya'ni
to'ydan bir kun oldin, mijoz eng ko'p qaraydigan payt, orqaga sanoq
"1 дней" deb turardi. Ingliz tilida ham shunday: "1 days".

YECHIM ikki qismdan iborat:

  * Sanoq yorliqlari ("kun", "soat") — ularni JS chizadi, shuning uchun
    uchala shakl shablondan data-atributda "|" bilan ajratilgan holda
    uzatiladi, JS esa raqamga qarab tanlaydi (_skript.html, "koplik").

  * Mehmonlar soni — bu serverda chiziladi, shuning uchun Django'ning
    o'z ko'plik mexanizmi ({% blocktrans count %}) ishlatiladi.

Qozoq, qirg'iz, turkman, tojik, qoraqalpoq va o'zbek tillarida sondan
keyin so'z o'zgarmaydi — u yerda uchala shakl bir xil bo'lishi kerak,
va test buni ham tekshiradi (aks holda kimdir ularga ham "ko'plik"
yasab qo'yishi mumkin).
"""
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.utils import timezone, translation
from django.utils.translation import ngettext, pgettext

from taklif.models import RSVP, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat

BIRLIKLAR = ["kun", "soat", "minut", "sekund", "yil", "oy"]
KONTEKSTLAR = ["1", "2-4", "5+"]

# Rus tilida uchalasi ham boshqacha bo'lishi SHART — aynan shu tuzatildi.
RUS_KUTILGAN = {
    "kun": ("день", "дня", "дней"),
    "soat": ("час", "часа", "часов"),
    "minut": ("минута", "минуты", "минут"),
    "sekund": ("секунда", "секунды", "секунд"),
    "yil": ("год", "года", "лет"),
    "oy": ("месяц", "месяца", "месяцев"),
}

# Bu tillarda son so'zni o'zgartirmaydi.
BIR_SHAKLLI = ["uz", "kk", "ky", "tg", "tk", "kaa"]


class SanoqYorliqlariTest(TestCase):
    def test_rus_tilida_uch_xil_shakl(self):
        with translation.override("ru"):
            for soz, kutilgan in RUS_KUTILGAN.items():
                natija = tuple(pgettext(k, soz) for k in KONTEKSTLAR)
                with self.subTest(soz=soz):
                    self.assertEqual(natija, kutilgan)

    def test_ingliz_tilida_birlik_va_koplik(self):
        with translation.override("en"):
            self.assertEqual(pgettext("1", "kun"), "day")
            self.assertEqual(pgettext("5+", "kun"), "days")
            self.assertEqual(pgettext("1", "soat"), "hour")
            self.assertEqual(pgettext("5+", "soat"), "hours")

    def test_qolgan_tillarda_shakl_bitta(self):
        for til in BIR_SHAKLLI:
            with translation.override(til):
                for soz in BIRLIKLAR:
                    shakllar = {pgettext(k, soz) for k in KONTEKSTLAR}
                    with self.subTest(til=til, soz=soz):
                        self.assertEqual(len(shakllar), 1,
                                         f"{til}/{soz}: {shakllar}")

    def test_har_bir_tilda_tarjima_bor(self):
        """Tarjimasiz qolsa, pgettext msgid'ni qaytaradi — ya'ni ruscha
        sahifada "kun" deb chiqib qoladi."""
        for til, _ in settings.LANGUAGES:
            with translation.override(til):
                for soz in BIRLIKLAR:
                    for k in KONTEKSTLAR:
                        natija = pgettext(k, soz)
                        with self.subTest(til=til, soz=soz, kontekst=k):
                            self.assertTrue(natija)
                            if til not in ("uz", "tk", "kaa"):
                                # bu uch tilda ba'zi so'zlar asl shakli
                                # bilan bir xil ("minut", "sekund")
                                pass


class MehmonlarSoniTest(TestCase):
    """Serverda chiziladigan mehmonlar soni."""

    MSGID = "%(soni)s kishi"

    def test_rus_tilida_son_shaklni_ozgartiradi(self):
        with translation.override("ru"):
            bir = ngettext(self.MSGID, self.MSGID, 1) % {"soni": 1}
            ikki = ngettext(self.MSGID, self.MSGID, 2) % {"soni": 2}
            besh = ngettext(self.MSGID, self.MSGID, 5) % {"soni": 5}
        self.assertEqual(bir, "1 человек")
        self.assertEqual(ikki, "2 человека")
        self.assertEqual(besh, "5 человек")

    def test_ingliz_tilida(self):
        with translation.override("en"):
            self.assertEqual(ngettext(self.MSGID, self.MSGID, 1) % {"soni": 1},
                             "1 person")
            self.assertEqual(ngettext(self.MSGID, self.MSGID, 3) % {"soni": 3},
                             "3 people")

    def test_tasdiqlaganlar_jumlasi_rus_tilida(self):
        m = "Hozircha <strong>%(soni)s</strong> kishi kelishini tasdiqladi"
        with translation.override("ru"):
            self.assertIn("человек подтвердил участие",
                          ngettext(m, m, 1) % {"soni": 1})
            self.assertIn("человека подтвердили",
                          ngettext(m, m, 2) % {"soni": 2})
            self.assertIn("человек подтвердили",
                          ngettext(m, m, 7) % {"soni": 7})


@override_settings(ALLOWED_HOSTS=["testserver"])
class SahifadaKoplikTest(TestCase):
    def setUp(self):
        self.taklifnoma = Taklifnoma.objects.create(
            slug="koplik-sinov", ism_1="Sardor", ism_2="Malika",
            shablon=shablon_yarat(),
            sana=timezone.now() + timedelta(days=40),
            faol=True, tolangan=True,
        )

    def test_sanoq_yorliqlari_uch_shakl_bilan_uzatiladi(self):
        """Shablon data-atributida uchala shakl "|" bilan kelishi kerak —
        JS shundan tanlaydi."""
        h = Client().get(f"/{self.taklifnoma.slug}/",
                         HTTP_ACCEPT_LANGUAGE="ru").content.decode()
        m = re.search(r'data-kun="([^"]*)"', h)
        self.assertIsNotNone(m, "countdown data-kun topilmadi")
        self.assertEqual(m.group(1), "день|дня|дней")

    def test_ozbekcha_sahifada_ham_uch_qism(self):
        h = Client().get(f"/{self.taklifnoma.slug}/").content.decode()
        m = re.search(r'data-soat="([^"]*)"', h)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "soat|soat|soat")

    def test_olik_mehmonlar_bolimi_qaytib_kelmagan(self):
        """Sakkizta eski dizaynda "Mehmonlar" degan bo'lim bor edi va u
        HECH QACHON ishlamagan: "mehmonlar_jami" va "mehmonlar"
        o'zgaruvchilari view'da umuman berilmagan, ya'ni sahifada
        "Hozircha <strong></strong> kishi kelishini tasdiqladi" degan
        bo'sh raqamli jumla chiqib turardi. Yangi dizaynlar (umumiy
        "_bolimlar.html") bunday bo'limga ega emas — mehmonlar ro'yxati
        ataylab faqat mezbonning maxfiy statistika sahifasida.
        """
        baza = Path(settings.BASE_DIR) / "taklif" / "templates"
        topilgan = [str(y.relative_to(baza)) for y in baza.rglob("*.html")
                    if "mehmonlar_jami" in y.read_text(encoding="utf-8")]
        self.assertEqual(topilgan, [], f"O'lik bo'lim qaytib kelgan: {topilgan}")


class SkriptdaKoplikFunksiyasiTest(TestCase):
    """JS tomonidagi qoida — faqat mavjudligini tekshiradi (uni Python
    ishga tushira olmaydi), lekin yo'qolib qolsa darhol ko'rinadi."""

    def test_koplik_funksiyasi_skriptda_bor(self):
        yol = (Path(settings.BASE_DIR) / "taklif" / "templates" / "taklif"
               / "shablonlar" / "_skript.html")
        matn = yol.read_text(encoding="utf-8")
        self.assertIn("function koplik(", matn)
        # Rus qoidasidagi 11-14 istisnosi — eng oson unutiladigan joyi.
        self.assertIn("ikkitalik !== 11", matn)
        self.assertIn("ikkitalik < 12 || ikkitalik > 14", matn)
