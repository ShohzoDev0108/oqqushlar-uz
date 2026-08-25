from django.db import migrations


def shablonlarni_qoshish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")

    # Mijoz yuborgan 9 ta ilhom-rasm asosida yaratilgan yangi dizaynlar.
    yangi = [
        {"nomi": "Sadaf", "kod": "sadaf", "narx": 200000, "turkum": "zamonaviy"},
        {"nomi": "Zarnigor", "kod": "zarnigor", "narx": 180000, "turkum": "zamonaviy"},
        {"nomi": "Shoyi", "kod": "shoyi", "narx": 180000, "turkum": "zamonaviy"},
        {"nomi": "Anor", "kod": "anor", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Ravoq", "kod": "ravoq", "narx": 200000, "turkum": "zamonaviy"},
        {"nomi": "Kumush", "kod": "kumush", "narx": 180000, "turkum": "zamonaviy"},
        {"nomi": "Qandil", "kod": "qandil", "narx": 180000, "turkum": "zamonaviy"},
        {"nomi": "Adras", "kod": "adras", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Nurafshon", "kod": "nurafshon", "narx": 200000, "turkum": "zamonaviy"},
    ]
    for maydonlar in yangi:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=[
        "sadaf", "zarnigor", "shoyi", "anor", "ravoq",
        "kumush", "qandil", "adras", "nurafshon",
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0013_alter_taklifnoma_ism_1_alter_taklifnoma_ism_2_and_more"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_qoshish, shablonlarni_ochirish),
    ]
