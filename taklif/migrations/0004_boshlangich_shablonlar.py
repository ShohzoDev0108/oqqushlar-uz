from django.db import migrations


def shablonlarni_yaratish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    boshlangich = [
        {"nomi": "Registon", "kod": "registon", "narx": 150000},
        {"nomi": "Sodda", "kod": "sodda", "narx": 100000},
    ]
    for maydonlar in boshlangich:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=["registon", "sodda"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0003_taklifnomarasm"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_yaratish, shablonlarni_ochirish),
    ]
