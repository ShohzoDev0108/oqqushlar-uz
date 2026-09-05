from django.db import migrations


# TAFTISH TOPILMASI.
#
# Dizaynlar sahifasi mijozdan birinchi navbatda marosim turini so'raydi.
# To'qqiz turdan OLTITASIDA ro'yxat butunlay bo'sh chiqardi:
#
#     Nikoh to'yi ....... 13 ta dizayn
#     Fotiha to'yi ...... 13 ta
#     Yubiley ........... 13 ta
#     Qiz uzatish ....... 0
#     Xatna to'yi ....... 0
#     Beshik to'yi ...... 0
#     Nahor oshi ........ 0
#     Tug'ilgan kun ..... 0
#     Boshqa ............ 0
#
# Ya'ni mijoz "Xatna to'yi"ni tanlasa, bo'sh sahifaga tushardi va yaratish
# yo'li shu yerda uzilardi. Sababi: barcha 13 ta ommaviy dizaynda
# marosim_turlari faqat ["toy", "fotiha_toy", "yubiley"] edi.
#
# NEGA SHUNDAY BO'LGAN. Cheklov asossiz emas edi: umumiy komponentlarda
# YURAK shakli shartsiz chizilardi — ochilish kartasi yurakka kesilardi
# va kalendarda marosim kuni yurak bilan belgilanardi. Beshik to'yi yoki
# nahor oshiga bu mos kelmasdi.
#
# Bu migratsiyadan OLDIN o'sha to'siq olib tashlangan: shakl endi
# Taklifnoma.juftlik_marosimi'ga qarab tanlanadi — juftlik marosimlarida
# (to'y, fotiha to'yi, yubiley) yurak, qolganlarida ravoq va neytral
# doira. Shundan keyingina dizaynlarni barcha turlarga ochish xavfsiz.
#
# Har bir dizaynni alohida saralamadik: dizaynlarning o'zi neytral —
# rang, naqsh va tipografikadan iborat, matnlar esa marosim turidan
# keladi. Aniq bir dizayn biror turga mos kelmasa, uni admin panelidan
# (Shablonlar -> Marosim turlari) belgilab qo'yish yetarli.

BARCHA_TURLAR = (
    "toy,fotiha_toy,qizlar_bazmi,sunnat_toy,beshik_toy,"
    "nahor_oshi,yubiley,tugilgan_kun,boshqa"
)

# Migratsiyani qaytarish kerak bo'lsa — avvalgi holat.
ESKI_TURLAR = "toy,fotiha_toy,yubiley"


def ochish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    # Faqat ommaviy dizaynlar. Yashiringanlariga (kumush, aurora, zarhal)
    # tegmaymiz — ular baribir tanlash sahifasida ko'rinmaydi.
    Shablon.objects.filter(ommaviy=True).update(marosim_turlari_raw=BARCHA_TURLAR)


def qaytarish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(ommaviy=True).update(marosim_turlari_raw=ESKI_TURLAR)


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0034_saytsozlamalari_instagram_saytsozlamalari_telefon"),
    ]

    operations = [
        migrations.RunPython(ochish, qaytarish),
    ]
