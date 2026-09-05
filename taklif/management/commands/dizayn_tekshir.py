# -*- coding: utf-8 -*-
"""Dizayn fayllari va bazadagi Shablon yozuvlari mos kelishini tekshiradi.

NEGA KERAK. Mijoz ko'radigan dizaynlar ro'yxati BAZADAGI Shablon
yozuvlaridan olinadi; sahifani chizadigan HTML esa
taklif/templates/taklif/shablonlar/<kod>.html faylidan. Bu ikkisi
bir-biridan mustaqil, ya'ni ular ajralib ketishi mumkin — va hech qanday
xato bermaydi:

  * FAYL BOR, YOZUV YO'Q — dizayn hech qachon ko'rinmaydi. Fayl
    repozitoriyada turaveradi, ustida ishlash mumkin, deploy qilish
    mumkin — natija esa nolga teng. (Aynan shunday bo'lgan: "zarnigor"
    0031 migratsiyasida katalogdan o'chirilgan, fayli qolgan, va uning
    ustida bir necha soat ish bajarilgan.)

  * YOZUV BOR, FAYL YO'Q — bundan ham yomoni: mijoz dizaynni tanlaydi,
    lekin taklifnoma butunlay boshqa ko'rinishda chiqadi, chunki
    views._shablon_fayli() jimgina standart shablonga tushib qoladi.

Ishlatish (deploydan OLDIN, statik_tekshir bilan birga):

    python manage.py dizayn_tekshir

Ikkinchi holat topilsa 1 qaytaradi (bu haqiqiy nosozlik). Birinchisi
faqat ogohlantirish — ba'zan fayl ataylab oldindan tayyorlab qo'yiladi.
"--qattiq" bilan ishga tushirilsa, u ham xato hisoblanadi.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from taklif.models import Shablon

# Bu fayllar shablon emas — umumiy qismlar (ular "_" bilan boshlanadi).
QISM_BELGISI = "_"


class Command(BaseCommand):
    help = "Dizayn HTML fayllari va bazadagi Shablon yozuvlari mosligini tekshiradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--qattiq",
            action="store_true",
            help="Yozuvsiz fayllarni ham xato deb hisoblaydi (nafaqat ogohlantirish).",
        )

    def handle(self, *args, **sozlamalar):
        papka = os.path.join(
            str(settings.BASE_DIR), "taklif", "templates", "taklif", "shablonlar"
        )
        if not os.path.isdir(papka):
            self.stdout.write(self.style.ERROR(f"Papka topilmadi: {papka}"))
            raise SystemExit(1)

        fayllar = {
            nom[:-5]
            for nom in os.listdir(papka)
            if nom.endswith(".html") and not nom.startswith(QISM_BELGISI)
        }

        yozuvlar = {s.kod: s for s in Shablon.objects.all()}
        ommaviy = {kod for kod, s in yozuvlar.items() if s.ommaviy}
        yashirin = set(yozuvlar) - ommaviy

        faylsiz = sorted(set(yozuvlar) - fayllar)     # yozuv bor, fayl yo'q
        yozuvsiz = sorted(fayllar - set(yozuvlar))    # fayl bor, yozuv yo'q

        self.stdout.write(
            f"Dizayn fayllari: {len(fayllar)} ta.  "
            f"Bazada: {len(yozuvlar)} ta yozuv "
            f"({len(ommaviy)} ommaviy, {len(yashirin)} yashirin)."
        )

        xato = False

        if faylsiz:
            xato = True
            self.stdout.write(
                self.style.ERROR(f"\nYOZUV BOR, FAYL YO'Q: {len(faylsiz)} ta")
            )
            for kod in faylsiz:
                holat = "ommaviy" if kod in ommaviy else "yashirin"
                self.stdout.write(f"  {kod}  ({holat})")
            self.stdout.write(
                self.style.WARNING(
                    "\nBu dizaynni tanlagan mijoz butunlay boshqa ko'rinishdagi\n"
                    "taklifnoma oladi — sahifa jimgina standart shablonga tushadi."
                )
            )

        if yozuvsiz:
            uslub = self.style.ERROR if sozlamalar["qattiq"] else self.style.WARNING
            self.stdout.write(uslub(f"\nFAYL BOR, BAZADA YOZUV YO'Q: {len(yozuvsiz)} ta"))
            for kod in yozuvsiz:
                self.stdout.write(f"  {kod}.html")
            self.stdout.write(
                self.style.WARNING(
                    "\nBu fayllar hech qachon ko'rsatilmaydi. Ular ustida qilingan\n"
                    "ish mijozga yetib bormaydi. Ko'rsatish uchun migratsiya bilan\n"
                    "Shablon yozuvi yaratish kerak."
                )
            )
            if sozlamalar["qattiq"]:
                xato = True

        if not xato and not yozuvsiz:
            self.stdout.write(self.style.SUCCESS("\nHammasi mos."))

        if xato:
            raise SystemExit(1)
