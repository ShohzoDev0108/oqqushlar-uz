# -*- coding: utf-8 -*-
"""Oqqushlar — qorong'i fonli brend to'plami (Telegram + Instagram).

Hamma fayl BITTA manbadan (taklif/static/taklif/gerb.svg) va BITTA
palitradan quriladi, shuning uchun to'plamdagi hech bir rasm boshqasidan
farq qilmaydi. Rangni yoki matnni o'zgartirish kerak bo'lsa — faqat
shu fayldagi o'zgaruvchilar tahrirlanadi va skript qayta ishga tushiriladi.
"""
import io, os
import cairosvg
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GERB  = "/mnt/user-data/uploads/oqqushlar_project/taklif/static/taklif/gerb.svg"
BELGI = "/mnt/user-data/uploads/oqqushlar_project/dizayn/logo/oqqushlar-belgi.svg"
CHIQISH = "brend"

# --- Palitra (saytdagi qiymatlar bilan bir xil) ---
FON_ASOS = "#14100c"   # chuqur iliq qora
NUR      = "#a9812e"   # orqa fondagi yumshoq oltin nur
OLTIN    = "#c9a227"   # chiziqlar va ikkinchi darajali matn
KREM     = "#f7f1e6"   # asosiy matn va logotip
TUMSHUQ  = "#e8b45e"

SERIF = "/tmp/CormorantGaramond.ttf"
SANS  = "/tmp/Manrope.ttf"

_svg = open(GERB, encoding="utf-8").read()
LOGO_SVG = (_svg.replace('fill="#a9812e"', f'fill="{KREM}"')
                .replace('fill="#17130f"', 'fill="#2a2118"')
                .replace('fill="#e27c20"', f'fill="{TUMSHUQ}"'))

# Soddalashtirilgan belgi — ikki oqqush bo'yni yurak hosil qiladi.
BELGI_SVG = open(BELGI, encoding="utf-8").read().replace("currentColor", KREM)


def shrift(yol, olcham, ogirlik=None):
    f = ImageFont.truetype(yol, olcham)
    if ogirlik is not None:
        try:
            f.set_variation_by_axes([ogirlik])
        except Exception:
            pass
    return f


def fon_yasa(w, h, markaz_y=None, kuch=30):
    """Qorong'i fon + markazda juda yumshoq oltin nur."""
    im = Image.new("RGB", (w, h), FON_ASOS)
    my = markaz_y if markaz_y is not None else h // 2
    m = Image.new("L", (w, h), 0)
    r = int(min(w, h) * 0.58)
    ImageDraw.Draw(m).ellipse([w // 2 - r, my - r, w // 2 + r, my + r], fill=kuch)
    m = m.filter(ImageFilter.GaussianBlur(min(w, h) * 0.24))
    return Image.composite(Image.new("RGB", (w, h), NUR), im, m)


def logo_rasm(balandlik):
    png = cairosvg.svg2png(bytestring=LOGO_SVG.encode(),
                           output_width=balandlik, output_height=balandlik)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def kengligi(matn, f, oraliq):
    """Harflar orasiga bo'shliq qo'shilgandagi umumiy kenglik."""
    if not matn:
        return 0
    return sum(f.getlength(h) for h in matn) + oraliq * (len(matn) - 1)


def matn_yoz(rasm, xy, matn, f, rang, oraliq=0, markaz=True):
    """Harflar orasiga bo'shliq (letter-spacing) qo'shib yozadi.

    PIL bunday bo'shliqni qo'llab-quvvatlamaydi, shuning uchun har bir
    harf alohida chiziladi. Lekin bo'shliq KERAK BO'LMAGANDA butun satr
    bitta chaqiruvda yoziladi: harfma-harf chizishda shrift kerningi
    yo'qoladi va kichik harflar bir-biriga yopishib qoladi
    ("oqqushlar" da "hl" ustma-ust tushardi — tekshirilgan)."""
    d = ImageDraw.Draw(rasm)
    x, y = xy
    if oraliq == 0:
        d.text((x, y), matn, font=f, fill=rang,
               anchor="mt" if markaz else "lt")
        return x
    if markaz:
        x -= kengligi(matn, f, oraliq) / 2
    for h in matn:
        d.text((x, y), h, font=f, fill=rang, anchor="lt")
        x += f.getlength(h) + oraliq
    return x


def hoshiya(rasm, chekka, qalinlik=None):
    d = ImageDraw.Draw(rasm)
    q = qalinlik or max(1, rasm.width // 900)
    d.rectangle([chekka, chekka, rasm.width - chekka, rasm.height - chekka],
                outline=OLTIN, width=q)


# ---------------------------------------------------------------- avatar
def avatar(N, fayl):
    """Telegram va Instagram avatari.

    Ikkala ilova ham avatarni DOIRA qilib kesadi, shuning uchun logotip
    kadrning 78% idan oshmaydi — burchaklarda hech narsa yo'q, kesilganda
    yo'qoladigan tafsilot ham yo'q.
    """
    p = fon_yasa(N, N, markaz_y=int(N * 0.48))
    lg = logo_rasm(int(N * 0.78))
    p.paste(lg, ((N - lg.width) // 2, (N - lg.height) // 2), lg)
    p.save(os.path.join(CHIQISH, fayl))
    return fayl


# ------------------------------------------------------------ post/story
def kartochka(w, h, fayl, logo_ulush=0.50, markaz_ulush=0.45,
              past_ulush=0.10, hoshiyali=True):
    """Post va story uchun umumiy maket: logotip, brend nomi, ingichka
    oltin chiziq, izoh va sayt manzili.

    Barcha o'lchamlar min(w, h) dan kelib chiqadi. Bu muhim: agar kenglik
    olinsa, 1280x720 li gorizontal kadrda yozuvlar balandlikka nisbatan
    haddan tashqari kattalashib, bir-birining ustiga chiqib ketardi
    (tekshirilgan).

    markaz_ulush — logotip+yozuv blokining vertikal markazi.
    past_ulush   — sayt manzilining pastdan masofasi. Story'da u kattaroq,
                   chunki kadrning pastki ~250px ini Instagram'ning o'z
                   tugmalari qoplaydi.
    """
    b = min(w, h)
    p = fon_yasa(w, h, markaz_y=int(h * markaz_ulush * 0.94))

    logo_h = int(b * logo_ulush)
    lg = logo_rasm(logo_h)
    blok_h = logo_h + int(b * 0.30)
    ust = int(h * markaz_ulush - blok_h / 2)
    p.paste(lg, ((w - lg.width) // 2, ust), lg)

    y = ust + logo_h + int(b * 0.045)
    f_nom = shrift(SERIF, int(b * 0.085), 600)
    matn_yoz(p, (w // 2, y), "OQQUSHLAR", f_nom, KREM, oraliq=b * 0.022)

    y += int(b * 0.105)
    d = ImageDraw.Draw(p)
    chiziq = int(b * 0.10)
    d.line([w // 2 - chiziq, y, w // 2 + chiziq, y], fill=OLTIN,
           width=max(1, b // 900))

    y += int(b * 0.038)
    f_izoh = shrift(SANS, int(b * 0.026), 500)
    matn_yoz(p, (w // 2, y), "RAQAMLI TAKLIFNOMALAR", f_izoh, OLTIN,
             oraliq=b * 0.011)

    # Manzil ORALIQSIZ yoziladi: keng oraliqda nuqta alohida belgi bo'lib
    # ajralib, "oqqushlar . uz" bo'lib o'qilardi.
    f_manzil = shrift(SANS, int(b * 0.028), 500)
    matn_yoz(p, (w // 2, h - int(b * past_ulush)), "oqqushlar.uz", f_manzil,
             KREM, oraliq=0)

    if hoshiyali:
        hoshiya(p, int(b * 0.045))
    p.save(os.path.join(CHIQISH, fayl))
    return fayl


def sodda_avatar(N, fayl, ulush=0.60):
    """Kichik o'lchamlar uchun avatar.

    NEGA IKKINCHI VARIANT KERAK: to'liq gerb — naqshli, ingichka chiziqli
    belgi. 512px da u ajoyib ko'rinadi, lekin Telegram va Instagram
    suhbatlar ro'yxatida avatar 44-64px bo'lib chiqadi va o'sha
    o'lchamda naqsh kul rang dog'ga aylanadi (o'lchandi). Soddalashtirilgan
    belgi esa 44px da ham aniq o'qiladi.
    """
    p = fon_yasa(N, N, markaz_y=N // 2)
    png = cairosvg.svg2png(bytestring=BELGI_SVG.encode(),
                           output_width=int(N * ulush), output_height=int(N * ulush))
    lg = Image.open(io.BytesIO(png)).convert("RGBA")
    p.paste(lg, ((N - lg.width) // 2, (N - lg.height) // 2), lg)
    p.save(os.path.join(CHIQISH, fayl))
    return fayl


def shaffof_logo(N, fayl):
    """Fonsiz oq logotip — mijozning o'z rasmi ustiga qo'yish uchun."""
    logo_rasm(N).save(os.path.join(CHIQISH, fayl))
    return fayl


if __name__ == "__main__":
    os.makedirs(CHIQISH, exist_ok=True)
    yasalgan = [
        sodda_avatar(512, "telegram-avatar-512.png"),
        sodda_avatar(1080, "instagram-avatar-1080.png"),
        avatar(512, "telegram-avatar-gerb-512.png"),
        avatar(1080, "instagram-avatar-gerb-1080.png"),
        kartochka(1080, 1080, "instagram-post-1080x1080.png",
                  logo_ulush=0.50, markaz_ulush=0.45),
        kartochka(1080, 1350, "instagram-post-1080x1350.png",
                  logo_ulush=0.52, markaz_ulush=0.45),
        # Story'da hoshiya yo'q: kadr chekkalarini Instagram o'z tugmalari
        # bilan qoplaydi va ramkaning yarmi ko'rinmay qolardi.
        kartochka(1080, 1920, "instagram-story-1080x1920.png",
                  logo_ulush=0.62, markaz_ulush=0.44, past_ulush=0.26,
                  hoshiyali=False),
        kartochka(1280, 720, "telegram-post-1280x720.png",
                  logo_ulush=0.50, markaz_ulush=0.42, past_ulush=0.09),
        shaffof_logo(2048, "logo-oq-shaffof-2048.png"),
    ]
    for f in yasalgan:
        yol = os.path.join(CHIQISH, f)
        print(f"{f:36s} {os.path.getsize(yol)//1024:5d} KB")
