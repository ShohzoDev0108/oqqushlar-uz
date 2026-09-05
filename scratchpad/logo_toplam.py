# -*- coding: utf-8 -*-
"""Brend belgisi variantlari to'plamini yaratadi.

MANBA: taklif/static/taklif/favicon.svg — ikkita oqqush yurak shaklida,
BITTA rangda (#a9812e) chizilgan sof vektor. Aynan bitta rang bo'lgani
uchun uni istalgan rangga qayta bo'yash mumkin, sifat yo'qotmasdan.

NEGA KERAK. Belgi bor, lekin uning holatlari yo'q edi:
  * to'q fonda (Telegram avatari, to'q dizaynli taklifnoma) oltin belgi
    yetarli ko'rinmaydi — oq variant kerak;
  * bir rangli bosma (muhr, blank, kashta) uchun to'q variant kerak;
  * eng muhimi — belgi KENG (nisbati ~1.77:1), avatar va favicon esa
    KVADRAT. To'g'ridan-to'g'ri kvadratga qo'yilganda qanot uchlari
    kesiladi va tepa-pastda katta bo'sh joy qoladi. Shuning uchun
    alohida KVADRAT kompozitsiya kerak: belgi doira ichiga bemalol
    sig'adigan qilib kichraytirilgan va markazlashtirilgan.

Kvadrat o'lcham hisobi: kengligi W, nisbati 1.77 bo'lgan belgining
diagonali W*1.148. Doira ichiga sig'ishi uchun W <= D/1.148 = 0.87*D.
Optik zaxira bilan W = 0.72*D olindi — qanot uchi doira chetiga tegmaydi.
"""
import pathlib
import re

MANBA = pathlib.Path("taklif/static/taklif/favicon.svg")
CHIQISH = pathlib.Path("taklif/static/taklif/logo")

ASL_RANG = "#a9812e"

# Brend ranglari
TILLA = "#a9812e"
OQ = "#ffffff"
QORA = "#17130f"
KREM = "#f6f1e8"
TOQ = "#12203a"
PUSHTI = "#dcaaa8"


def ichki_mazmun():
    src = MANBA.read_text(encoding="utf-8")
    m = re.match(r"<svg[^>]*>(.*)</svg>\s*$", src, re.S)
    assert m, "favicon.svg tuzilmasi kutilganidan boshqa"
    vb = re.search(r'viewBox="([^"]+)"', src).group(1)
    return m.group(1), vb


IZOH = ("<!-- Oqqushlar brend belgisi. Manba: favicon.svg. "
        "Bu fayl skript bilan yaratilgan: scratchpad/logo_toplam.py -->\n")


def keng(rang, nom):
    """Kenglikdagi asosiy belgi — sarlavha, blank, sayt uchun."""
    ich, vb = ichki_mazmun()
    ich = ich.replace(ASL_RANG, rang)
    x, y, w, h = [float(v) for v in vb.split()]
    return (f'{IZOH}<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="Oqqushlar">'
            f"{ich}</svg>\n")


def kvadrat(belgi_rang, fon_rang, halqa_rang=None, nom=""):
    """Kvadrat kompozitsiya — avatar, favicon, ijtimoiy tarmoq uchun."""
    ich, vb = ichki_mazmun()
    ich = ich.replace(ASL_RANG, belgi_rang)
    D = 512
    W = D * 0.72
    x0, y0, vw, vh = [float(v) for v in vb.split()]
    H = W * vh / vw
    px, py = (D - W) / 2, (D - H) / 2
    halqa = ""
    if halqa_rang:
        # Ingichka halqa — doira shaklida kesilganda ham, kvadratda ham
        # chiroyli chegara beradi.
        halqa = (f'<circle cx="{D/2}" cy="{D/2}" r="{D/2 - 14}" fill="none" '
                 f'stroke="{halqa_rang}" stroke-width="3" opacity=".55"/>')
    fon = f'<rect width="{D}" height="{D}" fill="{fon_rang}"/>' if fon_rang else ""
    return (f'{IZOH}<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {D} {D}" '
            f'width="{D}" height="{D}" role="img" aria-label="Oqqushlar">'
            f"{fon}{halqa}"
            f'<svg x="{px:.1f}" y="{py:.1f}" width="{W:.1f}" height="{H:.1f}" '
            f'viewBox="{vb}" preserveAspectRatio="xMidYMid meet">{ich}</svg>'
            f"</svg>\n")


FAYLLAR = {
    # Kenglikdagi belgi — uch rangda
    "belgi-tilla.svg": lambda: keng(TILLA, "tilla"),
    "belgi-oq.svg": lambda: keng(OQ, "oq"),
    "belgi-qora.svg": lambda: keng(QORA, "qora"),
    # Fonsiz kvadrat — mijoz o'z foniga qo'yishi uchun
    "kvadrat-tilla.svg": lambda: kvadrat(TILLA, None),
    "kvadrat-oq.svg": lambda: kvadrat(OQ, None),
    # Tayyor avatarlar — fon bilan
    "avatar-krem.svg": lambda: kvadrat(TILLA, KREM, TILLA),
    "avatar-toq.svg": lambda: kvadrat(TILLA, TOQ, TILLA),
    "avatar-pushti.svg": lambda: kvadrat(OQ, PUSHTI, OQ),
}


def main():
    CHIQISH.mkdir(parents=True, exist_ok=True)
    for nom, yasa in FAYLLAR.items():
        yol = CHIQISH / nom
        yol.write_text(yasa(), encoding="utf-8")
        print(f"  {nom:22} {yol.stat().st_size:6} bayt")


if __name__ == "__main__":
    main()
