from django.db import migrations, models


# Shablon.marosim_turi BITTA qiymat qabul qilardi — lekin amalda bitta
# dizayn bir nechta marosim turiga (masalan ham Nikoh, ham Fotiha to'yiga)
# mos bo'lishi kerak edi. Shu sabab bu maydon olib tashlanadi, o'rniga
# marosim_turlari_raw (vergul bilan ajratilgan ro'yxat) qo'shiladi — xuddi
# shu naqsh MusiqaVariant va NamunaRasm'ga ham qo'shiladi, shunda tayyor
# musiqa/rasm namunalarini ham marosim turiga qarab moslashtirish mumkin
# bo'ladi.
#
# Hozircha ommaviy 13 ta dizaynning barchasi "ikki ismli" (Aziz & Malika
# uslubidagi, romantik juftlik) ko'rinishda — shu sabab hammasi Nikoh
# to'yi + Fotiha to'yi + Yubileyga (IKKI_ISMLI_MAROSIM_TURLARI bilan bir
# xil) mos deb belgilanadi. Qiz uzatish va Xatna to'yiga hali maxsus
# dizayn yo'q — ular uchun alohida dizaynlar keyinroq qo'shiladi (shu
# vaqtgacha bu ikki marosim turi shablon tanlash sahifasida "hozircha
# dizayn yo'q" holatida qoladi — bu ataylab shunday).
IKKI_ISMLI_SHABLON_KODLARI = [
    "adras", "anor", "chinni", "kristall", "qandil", "qirgiz",
    "qozoq", "ravoq", "sadaf", "suzani", "tojik", "turkman", "zardoz",
]
IKKI_ISMLI_MAROSIM_TAGI = "toy,fotiha_toy,yubiley"


def marosim_turlarini_belgilash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=IKKI_ISMLI_SHABLON_KODLARI).update(
        marosim_turlari_raw=IKKI_ISMLI_MAROSIM_TAGI
    )


def marosim_turlarini_tozalash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=IKKI_ISMLI_SHABLON_KODLARI).update(
        marosim_turlari_raw=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0031_dizaynlar_katalogini_qisqartirish"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shablon",
            name="marosim_turi",
        ),
        migrations.AddField(
            model_name="shablon",
            name="marosim_turlari_raw",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Qaysi marosim turlariga mos — bir nechtasini belgilash "
                    "mumkin. Hech biri belgilanmasa, HECH BIR marosim "
                    'filtrida aniq mos sifatida ko\'rinmaydi (shablon tanlash '
                    'sahifasida "Barchasi" tanlanganda esa baribir '
                    "ko'rinadi)."
                ),
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="musiqavariant",
            name="marosim_turlari_raw",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Qaysi marosim turlariga mos — bir nechtasini belgilash "
                    "mumkin. Hech biri belgilanmasa, HECH BIR marosim "
                    'filtrida aniq mos sifatida ko\'rinmaydi (shablon tanlash '
                    'sahifasida "Barchasi" tanlanganda esa baribir '
                    "ko'rinadi)."
                ),
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="namunarasm",
            name="marosim_turlari_raw",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Qaysi marosim turlariga mos — bir nechtasini belgilash "
                    "mumkin. Hech biri belgilanmasa, HECH BIR marosim "
                    'filtrida aniq mos sifatida ko\'rinmaydi (shablon tanlash '
                    'sahifasida "Barchasi" tanlanganda esa baribir '
                    "ko'rinadi)."
                ),
                max_length=200,
            ),
        ),
        migrations.RunPython(
            marosim_turlarini_belgilash, marosim_turlarini_tozalash
        ),
    ]
