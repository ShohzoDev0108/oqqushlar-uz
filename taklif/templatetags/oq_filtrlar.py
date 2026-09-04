"""Oqqushlar sayti uchun kichik shablon filtrlari."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

# Uzuvchi bo'lmagan probel (U+00A0): raqam hech qachon qator oxirida
# "180" va "000" bo'lib ikkiga bo'linib ketmasligi uchun.
AJRATKICH = "\u00a0"


@register.filter
def narx_ajrat(qiymat):
    """Narxni mingliklarga ajratib ko'rsatadi: 180000 -> "180 000".

    Nega alohida filtr: Django'ning tayyor "intcomma" filtri vergul
    qo'yadi ("180,000") — o'zbek va rus tilida esa probel ishlatiladi.
    Uni probelga o'tkazish uchun esa settings.py'da
    USE_THOUSAND_SEPARATOR yoqilishi kerak bo'lardi, bu esa BUTUN
    saytga, jumladan formalardagi son maydonlariga ham ta'sir qiladi:
    input ichida "180 000" ko'rinishidagi qiymat qayta yuborilganda
    validatsiyadan o'tmay qolishi mumkin. Shu bois faqat ko'rsatish
    uchun ishlaydigan, hech narsaga tegmaydigan mustaqil filtr.
    """
    if qiymat is None or qiymat == "":
        return ""
    try:
        son = Decimal(str(qiymat)).quantize(Decimal("1"))
    except (InvalidOperation, ValueError, TypeError):
        return qiymat
    return f"{son:,}".replace(",", AJRATKICH)
