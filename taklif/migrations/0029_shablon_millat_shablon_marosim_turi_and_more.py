# Kategoriyalash loyihasi — 1-bosqich: Shablon'ga "millat" va "marosim_turi"
# maydonlari qo'shiladi, "turkum"dagi "Bolalar" o'rniga "Islomiy" keladi
# (faol shablonlarning birortasi ham "bolalar" qiymatida emas edi), va
# Taklifnoma.marosim_turi ro'yxatiga "Fotiha to'yi" qo'shiladi hamda
# "Sunnat to'yi" nomi "Xatna to'yi"ga almashtiriladi (ichki kod kaliti —
# "sunnat_toy" — o'zgarmaydi, faqat ko'rinadigan matn).

from django.db import migrations, models


def millatlarni_belgilash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod="qozoq").update(millat="qozoq")
    Shablon.objects.filter(kod="qirgiz").update(millat="qirgiz")
    Shablon.objects.filter(kod="tojik").update(millat="tojik")
    Shablon.objects.filter(kod="turkman").update(millat="turkman")
    Shablon.objects.filter(
        kod__in=["suzani", "zardoz", "chinni", "anor", "adras"]
    ).update(millat="ozbek")


def millatlarni_tozalash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.all().update(millat="")


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0028_taklifnoma_boshqa_tadbir_nomi_taklifnoma_ism_3_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taklifnoma",
            name="marosim_turi",
            field=models.CharField(
                choices=[
                    ("toy", "Nikoh to'yi"),
                    ("fotiha_toy", "Fotiha to'yi"),
                    ("qizlar_bazmi", "Qiz uzatish"),
                    ("sunnat_toy", "Xatna to'yi"),
                    ("beshik_toy", "Beshik to'yi"),
                    ("nahor_oshi", "Nahor oshi"),
                    ("yubiley", "Yubiley"),
                    ("tugilgan_kun", "Tug'ilgan kun"),
                    ("boshqa", "Boshqa"),
                ],
                default="toy",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="shablon",
            name="turkum",
            field=models.CharField(
                choices=[
                    ("zamonaviy", "Zamonaviy"),
                    ("milliy", "Milliy"),
                    ("islomiy", "Islomiy"),
                ],
                default="zamonaviy",
                help_text="Shablon tanlash sahifasida shu turkum ostida ko'rinadi",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="shablon",
            name="millat",
            field=models.CharField(
                blank=True,
                choices=[
                    ("ozbek", "O'zbek"),
                    ("qozoq", "Qozoq"),
                    ("qirgiz", "Qirg'iz"),
                    ("tojik", "Tojik"),
                    ("turkman", "Turkman"),
                    ("qoraqalpoq", "Qoraqalpoq"),
                    ("rus", "Rus"),
                ],
                default="",
                help_text=(
                    "Faqat turkum \"Milliy\" bo'lganda mantiqiy — shablon tanlash "
                    "sahifasida Milliy ichidagi millat filtrida shu bo'yicha "
                    "ko'rinadi. Bo'sh qoldirilsa, millat filtridan qat'i nazar "
                    "har doim ko'rinadi."
                ),
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="shablon",
            name="marosim_turi",
            field=models.CharField(
                blank=True,
                choices=[
                    ("toy", "Nikoh to'yi"),
                    ("fotiha_toy", "Fotiha to'yi"),
                    ("qizlar_bazmi", "Qiz uzatish"),
                    ("sunnat_toy", "Xatna to'yi"),
                    ("beshik_toy", "Beshik to'yi"),
                    ("nahor_oshi", "Nahor oshi"),
                    ("yubiley", "Yubiley"),
                    ("tugilgan_kun", "Tug'ilgan kun"),
                    ("boshqa", "Boshqa"),
                ],
                default="",
                help_text=(
                    "Agar shablon aynan shu marosim turiga (masalan Xatna "
                    "to'yiga) maxsus mo'ljallangan bo'lsa tanlang. Bo'sh "
                    "qoldirilsa — barcha marosim turlari uchun mos (universal) "
                    "hisoblanadi va har qanday marosim filtrida ko'rinadi."
                ),
                max_length=20,
            ),
        ),
        migrations.RunPython(millatlarni_belgilash, millatlarni_tozalash),
    ]
