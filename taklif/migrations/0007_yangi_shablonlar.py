from django.db import migrations


def shablonlarni_yaratish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    yangi = [
        {"nomi": "Gulbarg", "kod": "gulbarg", "narx": 150000},
        {"nomi": "Yulduz", "kod": "yulduz", "narx": 150000},
        {"nomi": "Atlas", "kod": "atlas", "narx": 150000},
    ]
    for maydonlar in yangi:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=["gulbarg", "yulduz", "atlas"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0006_marosim_turi_ism_musiqa_variant"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_yaratish, shablonlarni_ochirish),
    ]
