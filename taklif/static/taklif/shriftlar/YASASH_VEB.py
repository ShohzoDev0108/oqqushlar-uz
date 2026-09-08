# -*- coding: utf-8 -*-
"""Shu papkadagi .woff2 fayllarni QAYTA yasash uchun skript.

Odatda ishga tushirish SHART EMAS — tayyor fayllar repozitoriyda turadi.
Kerak bo'ladigan payt: shrift versiyasi yangilanganda yoki saytga yangi
alifboli til qo'shilganda.

NEGA O'ZIMIZDA SAQLAYMIZ. Ilgari shriftlar Google Fonts'dan yuklanardi.
Bu ikkita qo'shimcha domenga ulanishni talab qilardi (fonts.googleapis.com
CSS uchun, fonts.gstatic.com fayllar uchun) — har biri alohida DNS + TLS
qo'l berishi. O'zbekistondagi mobil internetda bu sezilarli kechikish.
Endi hamma narsa o'z domenimizdan, Cloudflare orqali keladi.

QAYSI SHRIFT NEGA:

  Manrope   — matn shrifti (sayt bo'ylab asosiy).
  Cormorant Garamond — sarlavhalar, ismlar, sana (nafislik uchun).

  Inter — QOZOQ, QIRG'IZ, TOJIK va QORAQALPOQ tillari uchun matn
      shrifti. Sabab: Manrope'da bu tillarning harflari YO'Q — kirill
      tomonda Ғ, Қ, Ң, Ұ, Ҳ, Ҷ, Ә, ӣ, ӯ; qoraqalpoqchada esa juda ko'p
      uchraydigan "ǵ". Brauzer yo'q harfni boshqa shriftdan olib qo'yadi
      va so'z ichida shrift almashib qoladi — "Қазан" yoki "maǵlıwmat"
      so'zining bitta harfi qolganlaridan boshqacha ko'rinadi.
      Shuning uchun bu to'rt tilda BUTUN matn Inter'ga o'tadi (u sakkiz
      tilimizning hammasini to'liq qoplaydi). Rus, ingliz va turkman
      tillari buni talab qilmaydi — Manrope ularni to'liq qoplaydi.

  EB Garamond (juda kichik qism) — faqat "Ǵ" va "ǵ" harflari uchun.
      Sabab: Cormorant'da aynan shu ikki harf yo'q, ular esa qoraqalpoq
      tilida kerak. Butun boshqa shriftni yuklamaslik uchun EB
      Garamond'dan faqat shu ikkita harf ajratib olingan (fayl ~3 KB) va
      CSS'da "unicode-range" bilan cheklangan — brauzer uni faqat sahifada
      "ǵ" harfi uchraganda yuklaydi.

Manba: Google Fonts'ning o'z fayllari, "fontsource" paketlari orqali.
Hammasi OFL-1.1 litsenziyasi ostida (litsenziya matnlari shu papkada).

ISHGA TUSHIRISH:

    npm install @fontsource-variable/manrope \\
                @fontsource-variable/cormorant-garamond \\
                @fontsource-variable/inter \\
                @fontsource-variable/eb-garamond
    pip install fonttools brotli
    python YASASH_VEB.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

BU_YER = Path(__file__).resolve().parent
PAKETLAR = BU_YER / "node_modules" / "@fontsource-variable"

# Qaysi paketdan qaysi qismlar olinadi va qanday nom bilan saqlanadi.
# "vietnamese" va "greek" qismlari OLINMAYDI — saytda bu tillar yo'q.
NUSXALAR = [
    ("manrope", "manrope", ["latin", "latin-ext", "cyrillic", "cyrillic-ext"], "normal"),
    ("cormorant-garamond", "cormorant", ["latin", "latin-ext", "cyrillic", "cyrillic-ext"], "normal"),
    ("cormorant-garamond", "cormorant-italic", ["latin", "latin-ext", "cyrillic", "cyrillic-ext"], "italic"),
    ("inter", "inter", ["latin", "latin-ext", "cyrillic", "cyrillic-ext"], "normal"),
]

LITSENZIYALAR = [
    ("manrope", "OFL-Manrope.txt"),
    ("cormorant-garamond", "OFL-CormorantGaramond.txt"),
    ("inter", "OFL-Inter.txt"),
    ("eb-garamond", "OFL-EBGaramond.txt"),
]


def nusxalar():
    for paket, nom, qismlar, uslub in NUSXALAR:
        for qism in qismlar:
            manba = PAKETLAR / paket / "files" / f"{paket}-{qism}-wght-{uslub}.woff2"
            maqsad = BU_YER / f"{nom}-{qism}.woff2"
            shutil.copyfile(manba, maqsad)
            print(f"  {maqsad.name}  ({maqsad.stat().st_size // 1024} KB)")


def qoraqalpoq_harflari():
    """EB Garamond'dan faqat "Ǵ" va "ǵ" ni ajratib oladi."""
    manba = PAKETLAR / "eb-garamond" / "files" / "eb-garamond-latin-ext-wght-normal.woff2"
    maqsad = BU_YER / "garamond-qq.woff2"
    subprocess.run(
        [sys.executable, "-m", "fontTools.subset", str(manba),
         "--unicodes=U+01F4-01F5",
         "--layout-features=",
         "--flavor=woff2",
         f"--output-file={maqsad}"],
        check=True,
    )
    print(f"  {maqsad.name}  ({maqsad.stat().st_size} bayt)")


def litsenziyalar():
    for paket, nom in LITSENZIYALAR:
        manba = PAKETLAR / paket / "LICENSE"
        if manba.exists():
            shutil.copyfile(manba, BU_YER / nom)
            print(f"  {nom}")


def qamrov_royxati():
    """Har bir faylda qaysi belgilar borligini "qamrov.json" ga yozadi.

    NEGA KERAK. "taklif/tests/test_shriftlar.py" testi har bir tilning
    harflari shriftlarda BOR ekanini tekshiradi. Test paytida shrift
    fayllarini o'qish uchun fontTools kerak bo'lardi — u esa loyihaning
    ishlashi uchun kerak emas, faqat shu skript uchun. Shuning uchun
    ro'yxat shu yerda, bir marta yasaladi va JSON bo'lib yotadi; test esa
    faqat JSON'ni o'qiydi.
    """
    import json

    from fontTools.ttLib import TTFont

    qamrov = {}
    for yol in sorted(BU_YER.glob("*.woff2")):
        belgilar = set()
        f = TTFont(yol)
        for jadval in f["cmap"].tables:
            belgilar |= set(jadval.cmap.keys())
        # Ro'yxatni ixcham saqlash uchun ketma-ket kodlar oraliqqa
        # birlashtiriladi: [[32, 126], [160, 255], ...]
        oraliqlar = []
        for kod in sorted(belgilar):
            if oraliqlar and kod == oraliqlar[-1][1] + 1:
                oraliqlar[-1][1] = kod
            else:
                oraliqlar.append([kod, kod])
        qamrov[yol.name] = oraliqlar
    (BU_YER / "qamrov.json").write_text(
        json.dumps(qamrov, indent=0, separators=(",", ":")), encoding="utf-8"
    )
    print(f"  qamrov.json ({len(qamrov)} ta fayl)")


if __name__ == "__main__":
    print("Shrift fayllari:")
    nusxalar()
    qoraqalpoq_harflari()
    print("Qamrov ro'yxati:")
    qamrov_royxati()
    print("Litsenziyalar:")
    litsenziyalar()
