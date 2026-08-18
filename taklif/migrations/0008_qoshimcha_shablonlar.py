from django.db import migrations


def shablonlarni_yaratish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    yangi = [
        {"nomi": "Zumrad", "kod": "zumrad", "narx": 150000},
        {"nomi": "Marmar", "kod": "marmar", "narx": 150000},
        {"nomi": "Bolajon", "kod": "bolajon", "narx": 150000},
    ]
    for maydonlar in yangi:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=["zumrad", "marmar", "bolajon"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0007_yangi_shablonlar"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_yaratish, shablonlarni_ochirish),
    ]
