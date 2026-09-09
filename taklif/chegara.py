# -*- coding: utf-8 -*-
"""So'rovlar chegarasi — bitta IP nechta marta yozishi mumkinligi.

TAFTISH TOPILMASI. Saytda django-axes bor edi, lekin u FAQAT login
sahifasini himoya qiladi. Mijoz uchun ochiq POST manzillarida esa hech
qanday cheklov yo'q edi:

  /yaratish/<shablon>/   — har bir so'rov bazaga yozuv qo'shadi va
                           R2'ga rasm/musiqa yuklaydi, ya'ni bu
                           TO'G'RIDAN-TO'G'RI PUL. Oddiy skript bir
                           kechada bazani ham, R2 hisobini ham
                           to'ldirib tashlashi mumkin edi.
  /<slug>/rsvp/          — istalgan odam havolani bilsa, mijozning
                           mehmonlar ro'yxatini soxta javoblar bilan
                           ko'mib tashlay olardi.

Bu yerda ataylab tashqi kutubxona ishlatilmaydi: ehtiyoj oddiy —
"bitta IP oynada N martadan ko'p yozmasin". Django'ning o'z kesh
tizimi buning uchun yetarli.

DIQQAT — KESH UMUMIY BO'LISHI SHART. Gunicorn bir nechta ishchi
jarayonda ishlaydi. Kesh xotirada (locmem) bo'lsa, har bir ishchining
o'z hisobi bo'lardi va haqiqiy chegara ishchilar soniga ko'payib
ketardi — ya'ni himoya "ishlayotgandek ko'rinib", aslida bir necha
barobar bo'sh bo'lardi. Shuning uchun bu yerda "default" emas,
bazaga asoslangan alohida "chegara" keshi ishlatiladi.

DIQQAT — IP MANZILGA ISHONISH. X-Forwarded-For sarlavhasini har kim
o'zi yozib yuborishi mumkin. Unga faqat sayt haqiqatan ishonchli
proksi (bizda — Cloudflare) ortida turganda ishonamiz, buni esa
DJANGO_BEHIND_PROXY sozlamasi belgilaydi. Aks holda soxta sarlavha
bilan chegarani chetlab o'tish mumkin bo'lardi.
"""
import logging
import time
from functools import wraps

from django.conf import settings
from django.core.cache import caches
from django.shortcuts import render

jurnal = logging.getLogger("taklif.chegara")

# Chegaralar: (nechta so'rov, necha soniya ichida).
#
# Raqamlar HALOL mijozning eng shov-shuvli holatiga qarab tanlangan,
# o'rtachaga emas — chegara oddiy odamni to'sib qo'ysa, u xato hisoblanadi.
#
# Taklifnoma yaratish: bitta mijoz odatda 1-2 ta yaratadi. 10 ta — bu
# "bir necha marta o'ylanib, qayta yaratdi" degan holat ham sig'adigan son.
YARATISH_CHEGARASI = (10, 60 * 60)

# RSVP: butun oila bitta telefondan javob berishi mumkin, to'yxonada esa
# o'nlab mehmon bitta Wi-Fi orqali kiradi — ya'ni bitta IP dan ko'p javob
# KUTILADIGAN holat. Shuning uchun chegara baland.
RSVP_CHEGARASI = (40, 60 * 60)

# Mehmon qo'shish: mezbon ro'yxatni bir o'tirishda kiritadi. Bu manzil
# maxfiy token talab qiladi, ya'ni xavf pastroq — chegara faqat
# tasodifiy sikl (masalan buzuq skript) uchun.
MEHMON_CHEGARASI = (200, 60 * 60)


def mijoz_ip(request):
    """So'rov kelgan haqiqiy IP.

    Cloudflare ortida REMOTE_ADDR — Cloudflare serverining manzili,
    ya'ni barcha mijozlar bitta IP dan kelgandek ko'rinadi. Haqiqiy
    manzil CF-Connecting-IP sarlavhasida.
    """
    if getattr(settings, "ISHONCHLI_PROKSI", False):
        cloudflare = request.META.get("HTTP_CF_CONNECTING_IP")
        if cloudflare:
            return cloudflare.strip()
        yonaltirilgan = request.META.get("HTTP_X_FORWARDED_FOR")
        if yonaltirilgan:
            # Ro'yxatdagi BIRINCHI manzil — asl mijoz.
            return yonaltirilgan.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "nomalum"


def chegara(nom, chegarasi):
    """POST so'rovlarini IP bo'yicha cheklaydigan dekorator.

    Faqat POST cheklanadi: sahifani ochib ko'rish (GET) bepul va
    zararsiz, uni cheklash esa qidiruv tizimlariga ham xalaqit berardi.
    """
    soni, oyna = chegarasi

    def dekorator(korinish):
        @wraps(korinish)
        def orovchi(request, *args, **kwargs):
            if request.method != "POST":
                return korinish(request, *args, **kwargs)

            ip = mijoz_ip(request)
            kalit = f"chegara:{nom}:{ip}"
            hozir = time.time()

            # Kesh ichida oxirgi urinishlar vaqti turadi — shundan
            # oynadan chiqib ketganlari tashlanadi ("sirg'aluvchi oyna").
            # Oddiy hisoblagichdan farqi: oyna chegarasida to'satdan
            # ikki barobar so'rov o'tib ketmaydi.
            kesh = caches["chegara"]
            urinishlar = [t for t in kesh.get(kalit, []) if hozir - t < oyna]

            if len(urinishlar) >= soni:
                jurnal.warning(
                    "So'rovlar chegarasi oshdi: %s, IP %s (%s ta / %s soniya)",
                    nom, ip, len(urinishlar), oyna,
                )
                return render(request, "taklif/juda_kop.html", status=429)

            urinishlar.append(hozir)
            kesh.set(kalit, urinishlar, oyna)
            return korinish(request, *args, **kwargs)

        return orovchi

    return dekorator
