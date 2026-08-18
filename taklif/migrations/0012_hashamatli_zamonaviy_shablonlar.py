from django.db import migrations


def shablonlarni_qoshish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")

    # Eng zamonaviy va jimjimador (hashamatli) uch dizayn — glassmorfizm,
    # kristall fasetalar va qora-oltin lyuks uslub. "Zamonaviy" turkumida,
    # eng yuqori narx toifasida (premium).
    yangi = [
        {"nomi": "Aurora", "kod": "aurora", "narx": 200000, "turkum": "zamonaviy"},
        {"nomi": "Kristall", "kod": "kristall", "narx": 200000, "turkum": "zamonaviy"},
        {"nomi": "Zarhal", "kod": "zarhal", "narx": 200000, "turkum": "zamonaviy"},
    ]
    for maydonlar in yangi:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(kod__in=["aurora", "kristall", "zarhal"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0011_milliy_shablonlar"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_qoshish, shablonlarni_ochirish),
    ]
