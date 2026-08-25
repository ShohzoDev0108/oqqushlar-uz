from django.db import migrations
from django.db.models.deletion import ProtectedError

# Loyihaning eng boshida yaratilgan, eng oddiy va eng arzon 8 ta shablon —
# mijoz talabiga ko'ra butunlay olib tashlanmoqda. Bularda yangi imkoniyatlar
# (kalendar, RSVP stepper, ulashish tugmalari va h.k.) ham yo'q edi.
ESKI_ODDIY_SHABLONLAR = [
    "registon",
    "sodda",
    "gulbarg",
    "yulduz",
    "atlas",
    "zumrad",
    "marmar",
    "bolajon",
]


def olib_tashlash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    for kod in ESKI_ODDIY_SHABLONLAR:
        try:
            Shablon.objects.filter(kod=kod).delete()
        except ProtectedError:
            # Agar shu shablondan foydalangan real mijoz taklifnomasi bor
            # bo'lsa (ForeignKey PROTECT), uni o'chira olmaymiz — mijozning
            # eski taklifnomasi buzilib qolmasligi uchun shunchaki ommaviy
            # ro'yxatdan (galereyadan) yashiramiz.
            Shablon.objects.filter(kod=kod).update(ommaviy=False)


def qaytarish(apps, schema_editor):
    # To'liq teskari qaytarish (ma'lumotlarni tiklash) mumkin emas — bu
    # ataylab qilingan o'chirish. Agar qandaydir sabab bilan hali ham
    # mavjud bo'lsa (ProtectedError yo'li), kamida ommaviy ro'yxatga
    # qaytaramiz.
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=ESKI_ODDIY_SHABLONLAR).update(ommaviy=True)


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0014_ilhom_shablonlar"),
    ]

    operations = [
        migrations.RunPython(olib_tashlash, qaytarish),
    ]
