from django.db import migrations


# Dizaynlar katalogini sifat bo'yicha qisqartirish (suhbatda batafsil ko'rib
# chiqilgan — 19 ta ommaviy dizaynning bir qismi shunchaki umumiy
# gradient/bo'sh karta edi, nomi va'da qilgan haqiqiy milliy naqshni
# ko'rsatmasdi):
#  - Shoyi, Nurafshon, Zarnigor — hech qanday taklifnomada ishlatilmagan,
#    xavfsiz butunlay o'chiriladi.
#  - Kumush, Aurora, Zarhal — ba'zi (hali to'lanmagan) qoralama
#    taklifnomalar shu shablonlarga bog'langan (Taklifnoma.shablon
#    on_delete=PROTECT bo'lgani uchun butunlay o'chirib bo'lmaydi) — shu
#    sabab bular faqat YASHIRILADI (ommaviy=False): yangi mijozlarga
#    Shablon tanlash sahifasida ko'rinmaydi, lekin eski qoralamalar
#    buzilmaydi.
# kod (slug) bo'yicha filtrlanadi, id bo'yicha emas — turli muhitlarda
# (lokal/production) Shablon id'lari bir xil bo'lishi shart emas.
OCHIRILADIGAN_KODLAR = ["shoyi", "nurafshon", "zarnigor"]
YASHIRILADIGAN_KODLAR = ["kumush", "aurora", "zarhal"]


def qisqartirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=OCHIRILADIGAN_KODLAR).delete()
    Shablon.objects.filter(kod__in=YASHIRILADIGAN_KODLAR).update(ommaviy=False)


def qaytarish(apps, schema_editor):
    # OCHIRILADIGAN_KODLAR qaytarilmaydi — ular butunlay o'chirilgan, qayta
    # yaratish uchun yetarli ma'lumot (rasm, narx va h.k.) saqlanmagan.
    # Faqat yashirilganlar qaytadan ommaviy qilinadi.
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=YASHIRILADIGAN_KODLAR).update(ommaviy=True)


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0030_alter_taklifnoma_ism_3"),
    ]

    operations = [
        migrations.RunPython(qisqartirish, qaytarish),
    ]
