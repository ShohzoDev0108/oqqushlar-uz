"""Har bir tilning harflari shriftlarimizda BOR ekanini tekshiradi.

NEGA BU TEST BOR. Shriftni tanlashda oson o'tkazib yuboriladigan xato:
shrift lotin va rus alifbosida chiroyli ko'rinadi, lekin qozoq "Қ",
tojik "ҷ" yoki qoraqalpoq "ǵ" harfi unda YO'Q bo'ladi. Brauzer bunday
harfni jimgina boshqa shriftdan olib qo'yadi — natijada so'z ichida
shrift almashadi va matn "sinib" ko'rinadi. Xato ekranda ko'rinadi,
lekin faqat o'sha tilni ochib ko'rgan odamga.

Aynan shu xato Manrope'da topilgan edi: unda Ғ, Қ, Ң, Ұ, Ҳ, Ҷ, Ә, ӣ, ӯ
harflari ham, qoraqalpoqchada juda ko'p uchraydigan "ǵ" ham yo'q — ya'ni
qozoq, qirg'iz, tojik va qoraqalpoq tillari buzilib ko'rinardi. Endi bu
to'rt til Inter'ga o'tkazilgan. Test o'sha yechim joyida turganini va
kelajakda buzilmasligini kuzatadi.

QANDAY ISHLAYDI. Shrift fayllarini o'qish uchun fontTools kerak bo'lardi
— u loyihaning ishlashi uchun kerak emas. Shuning uchun har bir faylda
qanday belgilar borligi "qamrov.json" faylida saqlanadi (uni
"taklif/static/taklif/shriftlar/YASASH_VEB.py" yasaydi). Test faqat shu
JSON'ni va tarjima kataloglarini o'qiydi.
"""
import json
import re
import unicodedata
from pathlib import Path

from django.conf import settings
from django.test import TestCase

SHRIFTLAR = Path(settings.BASE_DIR) / "taklif" / "static" / "taklif" / "shriftlar"

# Qaysi tilda matn qaysi shrift bilan yoziladi. Bu jadval
# "templates/base.html"dagi ":root:lang(...)" qoidasining aynan o'zi —
# ikkalasi bir-biriga mos turishi kerak.
MATN_SHRIFTI = {
    "uz": "manrope", "ru": "manrope", "en": "manrope", "tk": "manrope",
    "kk": "inter", "ky": "inter", "tg": "inter", "kaa": "inter",
}

# Sarlavhalar, ismlar va sana hamma tilda Cormorant'da. Qoraqalpoqcha
# "Ǵ/ǵ" undan tashqarida — u "garamond-qq.woff2" faylidan olinadi,
# shuning uchun sarlavha qamroviga o'sha fayl ham qo'shiladi.
SARLAVHA_SHRIFTI = "cormorant"


def _qamrov():
    return json.loads((SHRIFTLAR / "qamrov.json").read_text(encoding="utf-8"))


def _belgilar(fayllar, qamrov):
    """Berilgan fayllardagi barcha belgilar to'plami."""
    bor = set()
    for nom in fayllar:
        for boshi, oxiri in qamrov[nom]:
            bor.update(range(boshi, oxiri + 1))
    return bor


def _til_harflari(til):
    """Tarjima katalogidagi tarjima matnlarida uchraydigan harflar."""
    yol = Path(settings.BASE_DIR) / "locale" / til / "LC_MESSAGES" / "django.po"
    if not yol.exists():
        return set()
    matn = yol.read_text(encoding="utf-8")
    # Faqat tarjima qatorlari (msgstr va uning davomi), msgid emas —
    # msgid har doim o'zbekcha, ya'ni til harflarini bermaydi.
    qatorlar = re.findall(r'^(?:msgstr(?:\[\d\])?\s+)?"(.*)"$', matn, re.M)
    return {c for c in "".join(qatorlar) if unicodedata.category(c).startswith("L")}


class ShriftQamroviTest(TestCase):
    def setUp(self):
        self.qamrov = _qamrov()

    def _fayllar(self, oila):
        return [n for n in self.qamrov if n.startswith(oila + "-")]

    def test_qamrov_fayli_bor(self):
        """Shriftlar yangilanganda "qamrov.json" ham qayta yasalishi
        kerak — YASASH_VEB.py buni o'zi qiladi."""
        self.assertTrue((SHRIFTLAR / "qamrov.json").exists())
        self.assertGreaterEqual(len(self.qamrov), 16)

    def test_har_bir_tilning_matn_harflari_qoplangan(self):
        for til, oila in MATN_SHRIFTI.items():
            harflar = _til_harflari(til)
            if not harflar:
                continue
            bor = _belgilar(self._fayllar(oila), self.qamrov)
            yoq = sorted({c for c in harflar if ord(c) not in bor})
            with self.subTest(til=til, shrift=oila):
                self.assertEqual(yoq, [], f"{oila} shriftida yo'q: {''.join(yoq)}")

    def test_har_bir_tilning_sarlavha_harflari_qoplangan(self):
        fayllar = self._fayllar(SARLAVHA_SHRIFTI) + ["garamond-qq.woff2"]
        bor = _belgilar(fayllar, self.qamrov)
        for til in MATN_SHRIFTI:
            harflar = _til_harflari(til)
            if not harflar:
                continue
            yoq = sorted({c for c in harflar if ord(c) not in bor})
            with self.subTest(til=til):
                self.assertEqual(yoq, [], f"Cormorant'da yo'q: {''.join(yoq)}")

    def test_qoraqalpoq_gi_harfi_alohida_fayldan(self):
        """Cormorant'da "Ǵ/ǵ" yo'q — shuning uchun kichik yordamchi fayl
        bor. Agar u yo'qolsa, qoraqalpoqcha ismlarda bitta harf boshqa
        shriftda chiqib qoladi."""
        qq = _belgilar(["garamond-qq.woff2"], self.qamrov)
        self.assertIn(ord("Ǵ"), qq)
        self.assertIn(ord("ǵ"), qq)
        cormorant = _belgilar(self._fayllar("cormorant"), self.qamrov)
        self.assertNotIn(ord("ǵ"), cormorant, "Cormorant yangilangan bo'lsa, "
                                              "yordamchi fayl endi kerak emas")

    def test_barcha_sayt_tillari_jadvalda(self):
        self.assertEqual({k for k, _ in settings.LANGUAGES}, set(MATN_SHRIFTI))


class ShriftlarCssTest(TestCase):
    """CSS bilan fayllar bir-biriga mos turishini tekshiradi."""

    def setUp(self):
        self.css = (SHRIFTLAR / "shriftlar.css").read_text(encoding="utf-8")

    def test_css_dagi_har_bir_fayl_mavjud(self):
        for nom in re.findall(r"url\('([^']+)'\)", self.css):
            with self.subTest(fayl=nom):
                self.assertTrue((SHRIFTLAR / nom).exists(), f"{nom} yo'q")

    def test_har_bir_fayl_css_da_ishlatilgan(self):
        ishlatilgan = set(re.findall(r"url\('([^']+)'\)", self.css))
        for yol in SHRIFTLAR.glob("*.woff2"):
            with self.subTest(fayl=yol.name):
                self.assertIn(yol.name, ishlatilgan, "ortiqcha fayl")

    def test_google_fonts_ga_murojaat_yoq(self):
        """Shriftlar o'z serverimizdan kelishi kerak — begona domenga
        ulanish sahifa ochilishini sekinlashtiradi."""
        baza = Path(settings.BASE_DIR)
        topilgan = []
        for papka in ("templates", "taklif/templates", "taklif/static"):
            for yol in (baza / papka).rglob("*"):
                if yol.suffix not in (".html", ".css") or not yol.is_file():
                    continue
                matn = yol.read_text(encoding="utf-8", errors="ignore")
                if re.search(r'(?:href=|url\()["\']?https://fonts\.g', matn):
                    topilgan.append(str(yol.relative_to(baza)))
        self.assertEqual(topilgan, [], f"Google Fonts havolasi qolgan: {topilgan}")
