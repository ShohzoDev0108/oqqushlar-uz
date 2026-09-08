"""Har bir tilning tarjimasi O'SHA TILNING alifbosida yozilganini tekshiradi.

NEGA BU TEST BOR. Tarjima kataloglarida jimgina to'planib qoladigan uch xil
xato bor va ularning uchalasi ham faqat o'sha tilni ochgan odamga ko'rinadi:

  1. YOZUV ARALASHUVI — lotin so'zining ichida kirill harfi qolib ketishi.
     Ko'zga bir xil ko'rinadi ("т" va "t"), lekin brauzer ularni boshqa
     shriftdan oladi va so'z "sinib" chiqadi. Bizda uchtasi topilgan edi:
     "tolтırasız", "kóriр", "tәsiylatların".

  2. ESKI IMLO — qoraqalpoq tili 2009-yilda apostrofli yozuvdan
     (a', o', u', g', n') diakritikali yozuvga (á, ó, ú, ǵ, ń) o'tgan.
     Katalogda ikkalasi aralash edi: bir joyda "kóriń", boshqa joyda
     "ko'riń". Qoraqalpoq o'quvchisi uchun bu saytni tayyor emas
     ko'rsatadi.

  3. BEGONA HARF — alifboda umuman yo'q harf ("ğ", "ź" kabi). Odatda
     boshqa tildan nusxa ko'chirilganda paydo bo'ladi.

Test tarjima matnlaridagi HAR BIR harfni o'sha tilning alifbosi bilan
solishtiradi. Yangi tarjima qo'shilganda yoki tuzatilganda shu yerda
ushlanadi.
"""
import re
import unicodedata
from pathlib import Path

from django.conf import settings
from django.test import TestCase

# Har bir tilning alifbosi. Faqat harflar — tinish belgilari, raqamlar va
# lotin harflari (brend nomlari: "Telegram", "Instagram") tekshirilmaydi.
ALIFBO = {
    # O'zbek lotin: apostrof bilan (o', g') — bu o'zbekchada TO'G'RI.
    "uz": "abcdefghijklmnopqrstuvxyzoʻgʻ",
    "en": "abcdefghijklmnopqrstuvwxyz",
    # Qoraqalpoq, 2009-yildan keyingi alifbo. Apostrofli eski shakllar
    # (a', o', u', g', n') endi ishlatilmaydi — pastdagi alohida test
    # ularni ushlaydi.
    "kaa": "abdefghijklmnopqrstuvwxyzáǵíńóúıc",
    # Turkman lotin.
    "tk": "abçdefghijžklmnňoöpqrsştuüwyýzä",
    "ru": "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "kk": "абвгдеёжзийклмнопрстуфхцчшщъыьэюяәғқңөұүһі",
    "ky": "абвгдеёжзийклмнопрстуфхцчшщъыьэюяңөү",
    "tg": "абвгдеёжзийклмнопрстуфхчшъэюяғқҳҷӣӯ",
}

# Tarjimalarda ataylab qoladigan lotin so'zlari (brend va texnik nomlar) —
# kirill tillarida ular tekshiruvdan chiqariladi.
LOTIN_ISTISNO = re.compile(r"[A-Za-z]")


def _tozala(matn):
    """Tekshiruvdan chiqariladigan bo'laklarni olib tashlaydi.

    * "%(sarlavha)s" kabi o'rin egallovchilar — ular kod, tarjima emas;
    * katta harf bilan boshlanadigan yoki butunlay katta harfli lotin
      so'zlari — brend va qisqartmalar ("Telegram", "RSVP", "PDF") hamda
      misoldagi ismlar ("Sewinch"). Ular ataylab tarjima qilinmaydi.
    """
    matn = re.sub(r"%\([^)]*\)[sd]|%[sd]", " ", matn)
    return re.sub(r"\b[A-Z][A-Za-z]*\b", " ", matn)


def _tarjimalar(til):
    """Katalogdagi barcha TARJIMA matnlari (msgid emas).

    Fayl boshidagi xizmat bloki (msgid "") o'tkazib yuboriladi — u
    tarjima emas, "Content-Type" kabi texnik sozlamalar.
    """
    yol = Path(settings.BASE_DIR) / "locale" / til / "LC_MESSAGES" / "django.po"
    if not yol.exists():
        return []
    natija, ichida, xizmat = [], False, False
    oldingi = ""
    for qator in yol.read_text(encoding="utf-8").splitlines():
        if qator.startswith("msgid "):
            xizmat = qator == 'msgid ""'
        m = re.match(r'^msgstr(?:\[\d\])?\s+"(.*)"$', qator)
        if m:
            ichida = True
            if not xizmat:
                natija.append(_tozala(m.group(1)))
            continue
        m = re.match(r'^"(.*)"$', qator)
        if ichida and m:
            if not xizmat:
                natija.append(_tozala(m.group(1)))
            continue
        ichida = False
    return natija


class TarjimaAlifbosiTest(TestCase):
    def test_har_bir_til_oz_alifbosida(self):
        for til, alifbo in ALIFBO.items():
            ruxsat = set(alifbo) | set(alifbo.upper())
            begona = {}
            for matn in _tarjimalar(til):
                for harf in matn:
                    if not unicodedata.category(harf).startswith("L"):
                        continue
                    if harf in ruxsat:
                        continue
                    # Kirill tillarida lotin harflari brend nomlari
                    # ("Telegram", "PDF") — ular ataylab qoladi.
                    if til not in ("uz", "en", "kaa", "tk") and LOTIN_ISTISNO.match(harf):
                        continue
                    begona[harf] = begona.get(harf, 0) + 1
            with self.subTest(til=til):
                self.assertEqual(
                    begona, {},
                    f"{til} tarjimasida alifboga kirmaydigan harf: {begona}"
                )

    def test_barcha_sayt_tillari_tekshiriladi(self):
        self.assertEqual({k for k, _ in settings.LANGUAGES}, set(ALIFBO))


class QoraqalpoqEskiImloTest(TestCase):
    """Qoraqalpoq tili 2009-yilda apostrofli yozuvdan diakritikaga o'tgan.

    Eski shakl ("ko'riń") bilan yangisi ("kóriń") bir faylda aralash
    turgan edi. Bu test eskisining qaytib kelishini ushlaydi.
    """

    # Atoqli otdan keyingi apostrof (Telegram'da) — bu boshqa narsa,
    # qo'shimchani ajratish uchun, va u qoladi.
    ESKI = re.compile(r"(?<![A-Z])[aouognAOUOGN]'(?=[a-zıńáǵóú])")

    def test_eski_apostrofli_imlo_yoq(self):
        topilgan = []
        for matn in _tarjimalar("kaa"):
            topilgan += [m.group(0) for m in self.ESKI.finditer(matn)]
        self.assertEqual(topilgan, [], f"Eski imlo qaytib kelgan: {topilgan}")
