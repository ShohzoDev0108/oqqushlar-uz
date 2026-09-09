# -*- coding: utf-8 -*-
"""Kirill yozuvidagi ismlarni havolaga yaroqli lotin yozuviga o'girish.

TAFTISH TOPILMASI. Django'ning slugify() funksiyasi lotin bo'lmagan
harflarni shunchaki TASHLAB YUBORADI. Ya'ni mijoz ismini kirillda yozsa:

    slugify("Шоҳзод-Дилноза")  ->  ""

va havola "taklifnoma" bo'lib qolardi. Ikkinchi kirill mijoz kelsa —
"taklifnoma-20-05", uchinchisiga — "taklifnoma-toy". Ya'ni:

  — havolada mijozning ismi umuman ko'rinmasdi, holbuki butun mahsulot
    g'oyasi "sayt.uz/sardor-malika" kabi chiroyli havola berish edi;
  — mehmonlarning shaxsiy havolasi ham shunday: "mehmon", "mehmon-2",
    "mehmon-3" — mehmon o'z ismini emas, raqamini ko'rardi.

O'zbekistonda kirillda yozish hali ham keng tarqalgan, ya'ni bu kamdan-kam
uchraydigan chekka holat emas.

QAMROV. Jadval o'zbek kirillicha uchun tuzilgan, lekin rus, qozoq, qirg'iz
va tojik alifbolarining o'ziga xos harflari ham kiritilgan — sayt shu
tillarda ishlaydi va mijoz ismini o'z tilida yozishi tabiiy.

QOIDA: bu yerda faqat TRANSLITERATSIYA bo'ladi. Qisqartirish, bo'sh
natijani almashtirish va band havolani topish — chaqiruvchi kodning ishi.
"""

# Ayirish/yumshatish belgisidan keyingi unlilar. Bular bir harfli
# jadvaldan OLDIN qo'llanadi, aks holda "ъ" avval bo'shliqqa aylanib,
# keyingi harf noto'g'ri o'girilardi ("подъезд" -> "podezd" kerak).
_BIRIKMALAR = (
    ("ъе", "e"), ("ъё", "yo"), ("ъю", "yu"), ("ъя", "ya"),
    ("ье", "e"), ("ьё", "yo"), ("ью", "yu"), ("ья", "ya"),
)

# Bir harfli moslik. Kalitlar KICHIK harfda — matn oldindan pastga
# tushiriladi, chunki natija baribir kichik harfli havola bo'ladi.
#
# DIQQAT: o'zbek lotin yozuvida "Ў" -> "o'" va "Ғ" -> "g'" bo'ladi, lekin
# apostrof havolada ishlamaydi. Shuning uchun bu yerda oddiy "o" va "g"
# olinadi: "gulnora" — "gulno-ra" dan ancha yaxshi.
_HARFLAR = {
    # umumiy kirill
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # o'zbek kirilligiga xos
    "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
    # qozoq
    "ә": "a", "ұ": "u", "ү": "u", "һ": "h", "і": "i", "ң": "ng", "ө": "o",
    # tojik
    "ӣ": "i", "ӯ": "u", "ҷ": "j",
}


def kirilldan_lotinga(matn):
    """Kirill harflarini lotinga o'giradi, qolganini tegmasdan qoldiradi.

    Lotin yozuvidagi matn o'zgarishsiz qaytadi (faqat kichik harfga
    tushadi), ya'ni bu funksiyani har doim chaqirsa bo'ladi — matn qaysi
    yozuvda ekanini oldindan tekshirish shart emas.
    """
    if not matn:
        return ""

    matn = matn.lower()
    for birikma, orni in _BIRIKMALAR:
        matn = matn.replace(birikma, orni)

    return "".join(_HARFLAR.get(belgi, belgi) for belgi in matn)
