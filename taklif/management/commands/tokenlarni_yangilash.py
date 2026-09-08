import secrets

from django.core.management.base import BaseCommand

from taklif.models import Taklifnoma


class Command(BaseCommand):
    """Barcha taklifnomalarning statistika_token qiymatini qaytadan generatsiya
    qiladi.

    NEGA KERAK. Bir muddat "Tayyor" sahifasi (/tayyor/<slug>/) egalikni
    tekshirmasdan ochilar edi — ya'ni slug'ni bilgan har qanday odam o'sha
    sahifadagi maxfiy statistika havolasini ko'ra olardi. Teshik yopildi,
    lekin AVVAL yig'ib olingan tokenlar hamon ishlaydi: token o'zgarmagunicha
    ular bilan mijoz statistikasiga (mehmonlar ro'yxati, telefon raqamlari,
    tilaklar) kirish mumkin. Shu buyruq eski tokenlarni butunlay bekor qiladi.

    MIJOZGA TA'SIRI. Statistika havolasi bazadan hisoblanadi, shuning uchun
    "Mening taklifnomalarim" va "Tayyor" sahifalarida mijoz DARHOL yangi
    havolani ko'radi — hech narsa yo'qolmaydi. Faqat mijoz eski havolani
    biror joyga (masalan Telegram'ga o'ziga) saqlab qo'ygan bo'lsa, o'sha
    saqlangan havola ishlamay qoladi va u saytdan yangisini olishi kerak.
    Mehmonlarga yuboriladigan taklifnoma havolasi (/<slug>/) o'zgarmaydi —
    unga bu buyruqning aloqasi yo'q.

    Ishlatilishi:

        python manage.py tokenlarni_yangilash --sinov
            (hech narsani o'zgartirmaydi, nechta yozuv tegishini ko'rsatadi)

        python manage.py tokenlarni_yangilash
            (haqiqiy yangilash — tasdiq so'raydi)

        python manage.py tokenlarni_yangilash --sorasin-mas
            (tasdiqsiz; skript/timer uchun)
    """

    help = "Barcha taklifnomalarning maxfiy statistika tokenini yangilaydi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sinov",
            action="store_true",
            help="Hech narsani o'zgartirmasdan, nechta token yangilanishini ko'rsatadi.",
        )
        parser.add_argument(
            "--sorasin-mas",
            action="store_true",
            dest="sorasin_mas",
            help="Tasdiq so'ramasdan darhol yangilaydi.",
        )

    def handle(self, *args, **options):
        # Faqat "tirik" taklifnomalar muhim: butunlay o'chirilganlariga token
        # ham keraksiz. Lekin chiqindidagilar (ochirilgan_vaqt to'ldirilgan)
        # tiklanishi mumkin, shuning uchun ular ham yangilanadi — ya'ni
        # hammasi.
        soni = Taklifnoma.objects.count()

        if soni == 0:
            self.stdout.write("Bazada taklifnoma yo'q — yangilanadigan token ham yo'q.")
            return

        if options["sinov"]:
            self.stdout.write(
                self.style.WARNING(
                    f"[SINOV] {soni} ta taklifnomaning tokeni yangilangan bo'lardi. "
                    "Hech narsa o'zgartirilmadi."
                )
            )
            return

        if not options["sorasin_mas"]:
            self.stdout.write(
                f"{soni} ta taklifnomaning maxfiy statistika tokeni yangilanadi.\n"
                "Eski statistika havolalari BUTUNLAY ishlamay qoladi.\n"
                "Mijoz yangi havolani \"Mening taklifnomalarim\" sahifasidan oladi."
            )
            javob = input("Davom etamizmi? [ha/yo'q]: ").strip().lower()
            if javob not in ("ha", "h", "yes", "y"):
                self.stdout.write("Bekor qilindi — hech narsa o'zgartirilmadi.")
                return

        # Yangi tokenlar avval xotirada to'planadi, keyin bitta so'rov bilan
        # yoziladi. bulk_update tranzaksiya ichida ishlaydi: yo hammasi
        # yangilanadi, yo hech biri — yarim yangilangan holat bo'lmaydi.
        #
        # Takrorlanish xavfi: token_hex() 32 bayt (64 hex belgi) qaytaradi,
        # ya'ni 2^256 ehtimollik. Amalda to'qnashuv bo'lmaydi, lekin unique
        # cheklovi baribir bazada turibdi — agar mo'jiza yuz bersa, buyruq
        # IntegrityError bilan to'xtaydi va hech narsa yozilmaydi.
        yozuvlar = list(Taklifnoma.objects.only("pk"))
        for yozuv in yozuvlar:
            yozuv.statistika_token = secrets.token_hex()
        Taklifnoma.objects.bulk_update(yozuvlar, ["statistika_token"])

        self.stdout.write(
            self.style.SUCCESS(f"{soni} ta taklifnomaning tokeni yangilandi.")
        )
