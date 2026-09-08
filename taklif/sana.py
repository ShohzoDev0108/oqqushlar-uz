# -*- coding: utf-8 -*-
"""Marosim sanasini har bir tilning O'Z QOIDASI bo'yicha yozadi.

NEGA ALOHIDA MODUL. Django'ning `date` filtri bitta format qatoridan
("d-F, Y" kabi) nusxa ko'chiradi. Bu ko'p tillar uchun yetarli emas:

  * turkman tilida kun va yil TARTIB SON qo'shimchasini oladi va u
    unlilar uyg'unligiga qarab o'zgaradi — "12-nji", lekin "6-njy";
  * qirg'iz tilida yil ko'rsatilsa oy EGALIK shaklga o'tadi —
    "октябрь" emas, "октябры", va bu qo'shimcha ham uyg'unlikka
    bo'ysunadi ("июну", "апрели");
  * tojik tilida oyga IZOFA qo'shiladi — "октябри", va sana odatda
    "соли" so'zi bilan yoziladi;
  * rus tilida oy qaratqich kelishikda keladi — "октября".

Bularning birortasi ham format qatori bilan ifodalanmaydi. Shuning uchun
har bir til uchun alohida jadval va alohida yig'uvchi funksiya yozilgan.

MANBALAR. Quyidagi shakllar taxmin emas — har biri o'sha tildagi rasmiy
matnlardan olingan (davlat organlari saytlari, qonun matnlari, milliy
axborot agentliklari), CLDR va MediaWiki lokalizatsiya kataloglari bilan
solishtirilgan. Har bir til bo'limida qisqacha izoh bor.

NIMA UCHUN DJANGO KATALOGIGA TAYANMAYMIZ. Django'ning oy nomlari
tarjimalari hamma tilda ham to'g'ri emas: qoraqalpoq tili uchun Django'da
katalog umuman yo'q (u jimgina o'zbekchaga qaytadi va "oktabr" deb
ko'rsatadi, holbuki qoraqalpoqchada "oktyabr"), qolganlarida esa oy
nomlari bosh harf bilan yozilgan. Shuning uchun jadvallar shu yerda,
ko'z o'ngimizda turadi.
"""
from django.utils import translation

# ---------------------------------------------------------------------------
# O'ZBEK
# ---------------------------------------------------------------------------
# Shakl: "2026-yil 12-oktabr"
#
# Kun raqamdan keyin chiziqcha oladi — bu imlo qoidasi: "Tartib son arab
# raqamlari bilan yozilsa, -nchi qo'shimchasi o'rniga chiziqcha qo'yiladi"
# (O'zbek tilining asosiy imlo qoidalari, 1995, 56-§). O'sha qoidaning o'z
# misoli: "1991-yilning 1-sentabri" — ya'ni yil ham chiziqcha bilan, oy
# nomi ham kichik harf bilan.
#
# "sentabr/oktabr" — "y" holda: 2023-yilgi "O'zbek tilining katta imlo
# lug'ati" shu shaklni beradi, CLDR va glibc ham shunday. Amalda "oktyabr"
# ham uchraydi, lekin u lug'at me'yori emas.
OY_UZ = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentabr", 10: "oktabr", 11: "noyabr",
    12: "dekabr",
}

# ---------------------------------------------------------------------------
# QORAQALPOQ
# ---------------------------------------------------------------------------
# Shakl: "2026-jıl 12-oktyabr"
#
# DIQQAT: qoraqalpoqcha oy nomlari o'zbekchadan FARQ QILADI — ular "y"
# bilan yoziladi: sentyabr, oktyabr, noyabr, iyun, iyul, yanvar. Buni
# qoraqalpoq Vikipediyasidagi sana sahifalari ("18-oktyabr", "20-sentyabr",
# "6-iyul") va Qoraqalpog'iston Respublikasi sudi saytidagi qoraqalpoqcha
# matn ("2023-jıl 11-sentyabrde") tasdiqlaydi.
#
# Yil so'zi "jıl" — nuqtasiz "ı" bilan (o'zbekcha "yil" emas, qozoqcha
# "жыл" ham emas).
OY_KAA = {
    1: "yanvar", 2: "fevral", 3: "mart", 4: "aprel", 5: "may", 6: "iyun",
    7: "iyul", 8: "avgust", 9: "sentyabr", 10: "oktyabr", 11: "noyabr",
    12: "dekabr",
}

# ---------------------------------------------------------------------------
# RUS
# ---------------------------------------------------------------------------
# Shakl: "12 октября 2026"
#
# Sana ichida oy QARATQICH kelishikda keladi ("октября"), bosh kelishik
# ("Октябрь") faqat oy yakka turganda ishlatiladi. Aynan shu xato tuzatildi.
OY_RU = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая",
    6: "июня", 7: "июля", 8: "августа", 9: "сентября", 10: "октября",
    11: "ноября", 12: "декабря",
}

# ---------------------------------------------------------------------------
# TOJIK
# ---------------------------------------------------------------------------
# Shakl: "12-уми октябри соли 2026"
#
# Oyga IZOFA qo'shiladi ("октябр" -> "октябри"), kun tartib son shaklida
# ("12-уми"), yil esa "соли" so'zi bilan keladi. Bu shakl Tojikiston
# davlat axborot agentligi (khovar.tj) va "Asia-Plus" matnlarida doimiy
# uchraydi: "16 декабри соли 2025", "1-уми апрели соли 2025".
#
# DIQQAT: "май" izofada "майи" bo'ladi — "й" saqlanadi.
#
# Tojik tilida forsiy quyosh oylari ham bor (ҳамал, савр, ...), lekin ular
# fuqarolik sanalarida ishlatilmaydi — Navro'z, ziroat va she'riy
# kontekstlarda qoladi. Shuning uchun bu yerda rus tilidan o'zlashgan
# to'plam olingan.
OY_TG = {
    1: "январи", 2: "феврали", 3: "марти", 4: "апрели", 5: "майи",
    6: "июни", 7: "июли", 8: "августи", 9: "сентябри", 10: "октябри",
    11: "ноябри", 12: "декабри",
}

# ---------------------------------------------------------------------------
# QOZOQ
# ---------------------------------------------------------------------------
# Shakl: "2026 жылғы 12 қазан"
#
# Qozoq tili — bu ro'yxatdagi yagona til, unda oy nomlari rus tilidan
# olinmagan, o'z nomlari bor. Grammatikani "жылғы" so'zi ko'taradi, oy esa
# o'zgarmaydi — 12 oyning hammasi bosh shaklda qoladi. Chiziqcha
# ISHLATILMAYDI (qirg'iz va qoraqalpoqdan farqi shunda).
OY_KK = {
    1: "қаңтар", 2: "ақпан", 3: "наурыз", 4: "сәуір", 5: "мамыр",
    6: "маусым", 7: "шілде", 8: "тамыз", 9: "қыркүйек", 10: "қазан",
    11: "қараша", 12: "желтоқсан",
}

# ---------------------------------------------------------------------------
# QIRG'IZ
# ---------------------------------------------------------------------------
# Shakl: "2026-жылдын 12-октябры"
#
# Yil ko'rsatilganda oy EGALIK qo'shimchasini oladi va yumshoq belgi
# tushib qoladi: "октябрь" -> "октябры". Qo'shimcha to'rt xil bo'ladi
# (ы / и / у), oxirgi unliga qarab:
#     -ы : январь, февраль, март, май, сентябрь, октябрь, ноябрь, декабрь
#     -и : апрель (yagona)
#     -у : июнь, июль, август
# Barchasi Qirg'iziston Adliya vazirligi qonunlar bazasidagi matnlardan
# olingan ("2008-жылдын 17-октябры", "2003-жылдын 30-апрели",
# "1998-жылдын 11-июнундагы").
OY_KY = {
    1: "январы", 2: "февралы", 3: "марты", 4: "апрели", 5: "майы",
    6: "июну", 7: "июлу", 8: "августу", 9: "сентябры", 10: "октябры",
    11: "ноябры", 12: "декабры",
}

# ---------------------------------------------------------------------------
# TURKMAN
# ---------------------------------------------------------------------------
# Shakl: "2026-njy ýylyň 12-nji oktýabry"
#
# Eng murakkab holat: ham kun, ham yil tartib son qo'shimchasini oladi, va
# qo'shimcha ikki xil — "-nji" yoki "-njy". Tanlov son OG'ZAKI aytilganda
# oxirgi so'zning oxirgi unlisiga bog'liq (turkman unlilari: orqa qator
# a, y, o, u -> "-njy"; old qator ä, e, i, ö, ü -> "-nji").
#
# Amalda: 6 (alty), 9 (dokuz), 10 (on), 30 (otuz) bilan tugaganlar "-njy",
# qolganlari "-nji". Shuning uchun 2026 -> "2026-njy", 12 -> "12-nji".
# 2010 ("-njy") va 2020 ("-nji") juftligi qoidaning raqamga emas, aytilgan
# so'zga bog'liqligini isbotlaydi.
#
# Oy esa egalik shaklida keladi: "oktýabr" -> "oktýabry". Bitta istisno
# bor — "aprel" old qator unli bo'lgani uchun "apreli" bo'ladi. Bu oson
# o'tkazib yuboriladigan xato, shuning uchun testda alohida tekshiriladi.
OY_TK = {
    1: "ýanwary", 2: "fewraly", 3: "marty", 4: "apreli", 5: "maýy",
    6: "iýuny", 7: "iýuly", 8: "awgusty", 9: "sentýabry", 10: "oktýabry",
    11: "noýabry", 12: "dekabry",
}

# ---------------------------------------------------------------------------
# INGLIZ
# ---------------------------------------------------------------------------
# Shakl: "12 October 2026" — xalqaro (britancha) tartib. Amerikacha
# "October 12, 2026" ham to'g'ri, lekin taklifnomada kun-oy-yil tartibi
# ko'proq ishlatiladi va qolgan tillarimiz bilan ham mos tushadi.
OY_EN = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
    6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
    11: "November", 12: "December",
}


def _turkman_tartib(son):
    """Turkman tartib son qo'shimchasi: "-nji" yoki "-njy".

    Yuqoridagi izohga qarang. Nol bilan tugagan sonlarda oxirgi aytiladigan
    so'z — o'nlik nomi (on, ýigrimi, otuz, kyrk, elli, altmyş, ýetmiş,
    segsen, togsan), shuning uchun ular alohida qaraladi. Yuz va ming
    ("ýüz", "müň") old qator — ya'ni 2000, 1900 kabi sonlar "-nji" oladi.
    """
    oxirgi = son % 10
    if oxirgi == 0:
        onlik = (son // 10) % 10
        # on(10), otuz(30), kyrk(40), altmyş(60), togsan(90) -> orqa qator
        return "njy" if onlik in (1, 3, 4, 6, 9) else "nji"
    # alty(6), dokuz(9) -> orqa qator
    return "njy" if oxirgi in (6, 9) else "nji"


def _uz(s):
    return f"{s.year}-yil {s.day}-{OY_UZ[s.month]}"


def _kaa(s):
    return f"{s.year}-jıl {s.day}-{OY_KAA[s.month]}"


def _ru(s):
    return f"{s.day} {OY_RU[s.month]} {s.year}"


def _tg(s):
    return f"{s.day}-уми {OY_TG[s.month]} соли {s.year}"


def _kk(s):
    return f"{s.year} жылғы {s.day} {OY_KK[s.month]}"


def _ky(s):
    return f"{s.year}-жылдын {s.day}-{OY_KY[s.month]}"


def _tk(s):
    return (
        f"{s.year}-{_turkman_tartib(s.year)} ýylyň "
        f"{s.day}-{_turkman_tartib(s.day)} {OY_TK[s.month]}"
    )


def _en(s):
    return f"{s.day} {OY_EN[s.month]} {s.year}"


QURUVCHILAR = {
    "uz": _uz, "kaa": _kaa, "ru": _ru, "tg": _tg,
    "kk": _kk, "ky": _ky, "tk": _tk, "en": _en,
}


def uzun_sana(sana, til=None):
    """Sanani joriy (yoki ko'rsatilgan) tilda to'liq yozadi.

    `sana` — date yoki datetime. Vaqt zonasi bu yerda hisobga OLINMAYDI:
    chaqiruvchi tomon allaqachon mahalliy vaqtga o'tkazgan bo'lishi kerak
    (modeldagi "sana_uzun" xossasi shuni qiladi).

    Noma'lum til kelsa — masalan kelajakda saytga yangi til qo'shilsa-yu,
    bu yerga jadval qo'shish unutilsa — inglizcha shaklga qaytadi. Bu
    xatolikdan ko'ra yaxshiroq: sahifa baribir ochiladi. Testda esa
    "barcha tillar qamrab olingan" degan tekshiruv turibdi, ya'ni unutish
    testda ushlanadi.
    """
    if til is None:
        til = translation.get_language() or "uz"
    til = til.split("-")[0]
    return QURUVCHILAR.get(til, _en)(sana)
