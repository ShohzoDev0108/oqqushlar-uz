from django.db import migrations


# Marosimga MAXSUS dizaynlarni katalogga qo'shish.
#
# HOLAT. Bu yettita dizaynning HTML fayli allaqachon tayyor edi —
# har birining o'z palitrasi, o'z burchak bezagi (ramka-beshik-tl.png,
# ramka-xatna-tl.png va h.k. — 7 ta alohida chizma) va marosimga mos
# sarlavha mantiqi bor (masalan xatna to'yida "Amirbek va Islombeklarning
# xatna to'yi" — ikki-uch o'g'il uchun). Lekin bazada Shablon yozuvi
# yaratilmagani uchun ular hech qachon ko'rsatilmagan: mijoz "Xatna
# to'yi"ni tanlasa, umumiy to'y dizaynlarini olardi.
#
# Bu holat sezilmasligi mumkin edi, chunki hech qanday xato bermaydi —
# fayl bemalol turaveradi. Shuning uchun shu qadam bilan birga
# "dizayn_tekshir" buyrug'i ham qo'shildi: u endi fayl bilan baza
# ajralib ketganini deploydan oldin aytadi.
#
# HAR BIRI FAQAT O'Z marosimiga belgilanadi. Sababi: beshik to'yi
# dizaynini nikoh to'yiga taklif qilish mantiqsiz. Mijoz o'z marosimini
# tanlaganda ro'yxatda umumiy dizaynlar bilan birga shu maxsus dizayn
# ham chiqadi. Istisno — "tugilgankun": u "boshqa" (mijoz o'zi nom
# beradigan tadbir, masalan "11-sinf o'quvchilari") uchun ham mos.

DIZAYNLAR = [
    {
        "kod": "beshik", "nomi": "Beshik", "turkum": "milliy", "millat": "ozbek",
        "narx": 180000, "marosim_turlari_raw": "beshik_toy",
    },
    {
        "kod": "xatna", "nomi": "Xatna", "turkum": "milliy", "millat": "ozbek",
        "narx": 180000, "marosim_turlari_raw": "sunnat_toy",
    },
    {
        "kod": "qizuzatish", "nomi": "Qiz uzatish", "turkum": "milliy", "millat": "ozbek",
        "narx": 180000, "marosim_turlari_raw": "qizlar_bazmi",
    },
    {
        "kod": "nahoroshi", "nomi": "Nahor oshi", "turkum": "milliy", "millat": "ozbek",
        "narx": 180000, "marosim_turlari_raw": "nahor_oshi",
    },
    {
        "kod": "fotiha", "nomi": "Fotiha", "turkum": "milliy", "millat": "ozbek",
        "narx": 180000, "marosim_turlari_raw": "fotiha_toy",
    },
    {
        "kod": "tugilgankun", "nomi": "Tug'ilgan kun", "turkum": "zamonaviy", "millat": "",
        "narx": 180000, "marosim_turlari_raw": "tugilgan_kun,boshqa",
    },
    {
        "kod": "yubiley", "nomi": "Yubiley", "turkum": "zamonaviy", "millat": "",
        "narx": 180000, "marosim_turlari_raw": "yubiley",
    },
]


def qoshish(apps, schema_editor):
    Shablon = apps.get_model("taklif", "Shablon")
    for maydonlar in DIZAYNLAR:
        # get_or_create — migratsiya qayta ishga tushsa yoki kod allaqachon
        # qo'lda qo'shilgan bo'lsa, nusxa yaratmasin.
        Shablon.objects.get_or_create(
            kod=maydonlar["kod"],
            defaults={**maydonlar, "ommaviy": True},
        )


def qaytarish(apps, schema_editor):
    # Faqat hech bir taklifnomada ishlatilmaganlarini o'chiramiz —
    # Taklifnoma.shablon on_delete=PROTECT bo'lgani uchun ishlatilgani
    # baribir o'chmaydi va migratsiya xato bilan to'xtardi.
    Shablon = apps.get_model("taklif", "Shablon")
    kodlar = [d["kod"] for d in DIZAYNLAR]
    for shablon in Shablon.objects.filter(kod__in=kodlar):
        if not shablon.taklifnomalar.exists():
            shablon.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0035_dizaynlarni_barcha_marosimlarga_ochish"),
    ]

    operations = [
        migrations.RunPython(qoshish, qaytarish),
    ]
