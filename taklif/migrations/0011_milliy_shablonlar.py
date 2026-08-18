from django.db import migrations


def shablonlarni_sozlash(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")

    # Mavjud shablonlarning turkumini to'g'rilaymiz
    Shablon.objects.filter(kod="atlas").update(turkum="milliy")
    Shablon.objects.filter(kod="bolajon").update(turkum="bolalar")

    # Yangi milliy shablonlar — har bir xalqqa xos uslub
    yangi = [
        {"nomi": "Suzani", "kod": "suzani", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Zardo'z", "kod": "zardoz", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Chinni", "kod": "chinni", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Qozoq oyu", "kod": "qozoq", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Qirg'iz tunduk", "kod": "qirgiz", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Turkman gilam", "kod": "turkman", "narx": 180000, "turkum": "milliy"},
        {"nomi": "Tojik chakan", "kod": "tojik", "narx": 180000, "turkum": "milliy"},
    ]
    for maydonlar in yangi:
        Shablon.objects.get_or_create(kod=maydonlar["kod"], defaults=maydonlar)


def shablonlarni_ochirish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    Shablon.objects.filter(
        kod__in=["suzani", "zardoz", "chinni", "qozoq", "qirgiz", "turkman", "tojik"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0010_shablon_turkum"),
    ]

    operations = [
        migrations.RunPython(shablonlarni_sozlash, shablonlarni_ochirish),
    ]
