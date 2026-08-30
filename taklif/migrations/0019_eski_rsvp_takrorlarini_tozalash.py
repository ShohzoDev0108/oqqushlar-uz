# Qo'lda yozilgan ma'lumot-migratsiyasi (data migration).
#
# Sabab: 0020-migratsiya RSVP'ga (taklifnoma, mehmon) juftligi bo'yicha
# UniqueConstraint qo'shadi (bitta mehmon bitta taklifnomaga faqat bitta
# javobga ega bo'lishi kerak — aks holda mehmonlar soni bir necha barobar
# oshib ketishi mumkin edi, buni taftish paytida aniq test bilan isbotladik).
#
# Lekin bu cheklov qo'shilishidan OLDIN, xuddi shu bug tufayli baza ichida
# allaqachon (taklifnoma, mehmon) bo'yicha takrorlangan qatorlar bo'lishi
# mumkin (masalan mehmon sahifani ikki marta yangilagan bo'lsa). Agar
# shunday qatorlar bo'lsa, keyingi migratsiya (UniqueConstraint qo'shish)
# to'g'ridan-to'g'ri xato berib to'xtab qoladi.
#
# Shu uchun bu migratsiya avval har bir (taklifnoma, mehmon) guruhidan FAQAT
# eng oxirgi (yaratilgan vaqti bo'yicha eng yangi) javobni qoldirib,
# qolganlarini o'chiradi — "mehmonning eng so'nggi javobi haqiqiy javobi"
# degan mantiq bilan (xuddi yangi view kodidagi update_or_create bilan bir xil).
from django.db import migrations
from collections import defaultdict


def takrorlarni_tozalash(apps, schema_editor):
    RSVP = apps.get_model("taklif", "rsvp")
    guruhlar = defaultdict(list)
    qs = RSVP.objects.filter(mehmon__isnull=False).order_by("-yaratilgan", "-id")
    for yozuv in qs:
        guruhlar[(yozuv.taklifnoma_id, yozuv.mehmon_id)].append(yozuv.id)

    ochiriladigan_idlar = []
    for idlar in guruhlar.values():
        if len(idlar) > 1:
            # idlar allaqachon "-yaratilgan" bo'yicha saralangan (eng yangisi
            # birinchi) — birinchisini saqlab, qolganlarini o'chiramiz.
            ochiriladigan_idlar.extend(idlar[1:])

    if ochiriladigan_idlar:
        RSVP.objects.filter(id__in=ochiriladigan_idlar).delete()


def teskari(apps, schema_editor):
    # O'chirilgan takroriy qatorlarni tiklab bo'lmaydi — orqaga qaytarishning
    # hojati yo'q (ma'lumot yo'qotilmaydi, faqat haqiqiy takror yozuvlar
    # yig'ilib qolmaydi).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0018_saytsozlamalari"),
    ]

    operations = [
        migrations.RunPython(takrorlarni_tozalash, teskari),
    ]
