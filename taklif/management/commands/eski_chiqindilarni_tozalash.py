from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from taklif.models import CHIQINDI_SAQLASH_KUNLARI, Taklifnoma


class Command(BaseCommand):
    """Mijoz o'zi o'chirgan, "chiqindilar"da CHIQINDI_SAQLASH_KUNLARI kundan
    ortiq turgan FAOLLASHTIRILGAN taklifnomalarni butunlay o'chiradi.

    VPS'da bu buyruq kunlik systemd timer orqali avtomatik ishga tushiriladi
    (README/deploy hujjatiga qarang) — shuning uchun "chiqindilar" cheksiz
    to'planib qolmaydi. Qo'lda tekshirish/ishga tushirish uchun:

        python manage.py eski_chiqindilarni_tozalash
        python manage.py eski_chiqindilarni_tozalash --sinov   (hech narsani
            o'chirmasdan, nechta yozuv o'chirilishini ko'rsatadi)
    """

    help = (
        f"{CHIQINDI_SAQLASH_KUNLARI} kundan ortiq \"chiqindida\" turgan "
        "taklifnomalarni butunlay o'chiradi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sinov",
            action="store_true",
            help="Hech narsani o'chirmasdan, faqat nechta yozuv o'chirilishini ko'rsatadi.",
        )

    def handle(self, *args, **options):
        chegara = timezone.now() - timedelta(days=CHIQINDI_SAQLASH_KUNLARI)
        eskilar = Taklifnoma.objects.filter(
            ochirilgan_vaqt__isnull=False, ochirilgan_vaqt__lt=chegara
        )
        soni = eskilar.count()

        if soni == 0:
            self.stdout.write("O'chirish kerak bo'lgan eski chiqindi topilmadi.")
            return

        if options["sinov"]:
            for slug in eskilar.values_list("slug", flat=True):
                self.stdout.write(f"  — {slug}")
            self.stdout.write(
                self.style.WARNING(f"[SINOV] {soni} ta taklifnoma o'chirilgan bo'lardi.")
            )
            return

        eskilar.delete()
        self.stdout.write(
            self.style.SUCCESS(f"{soni} ta eski chiqindi taklifnoma butunlay o'chirildi.")
        )
