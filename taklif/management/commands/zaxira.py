# -*- coding: utf-8 -*-
"""Ma'lumotlar bazasining zaxira nusxasini olib, serverdan TASHQARIGA yuboradi.

NEGA KERAK. Taftishda aniqlandiki, loyihada umuman zaxira nusxa yo'q edi:
na skript, na taymer, na qo'lda olingan nusxa. Bitta noto'g'ri migratsiya,
disk nosozligi yoki admin panelida adashib bosilgan "o'chirish" — va barcha
pullik mijozlarning taklifnomasi, mehmonlar ro'yxati va RSVP javoblari
qaytarib bo'lmaydigan darajada yo'qolardi. Media fayllar R2'da nisbatan
xavfsiz, ammo PostgreSQL bazasi yagona nuqta edi.

UCH QOIDA, ular shu buyruqning butun mantig'ini belgilaydi:

1. NUSXA SERVERNING O'ZIDA YOTMASIN. Disk yonsa, nusxa ham yonadi. Shuning
   uchun fayl darhol R2'ga yuboriladi va mahalliy nusxa o'chiriladi.

2. NUSXA MEDIA BILAN BIR PAQIRDA TURMASIN. Agar ilova ishlatadigan kalit
   zaxiralarni ham o'chira olsa, buzilgan yoki noto'g'ri ishlagan kod
   ikkalasini birdan yo'q qiladi. Shu bois ZAXIRA_BUCKET alohida, va
   iloji bo'lsa kaliti ham alohida bo'lishi kerak.

3. OCHIQ MATNDA SAQLANMASIN. Bazada mijozlar va ularning mehmonlari
   haqidagi shaxsiy ma'lumot bor. Fayl gpg bilan shifrlanadi va shifrlash
   pg_dump chiqishidan TO'G'RIDAN-TO'G'RI quvur orqali o'tadi — ochiq matn
   diskka hech qachon yozilmaydi.

ISHLATISH:

    venv/bin/python manage.py zaxira              # nusxa olish va yuborish
    venv/bin/python manage.py zaxira --royxat     # mavjud nusxalar ro'yxati
    venv/bin/python manage.py zaxira --tekshir    # oxirgi nusxa o'qilishini sinash
    venv/bin/python manage.py zaxira --sinov      # hech narsa yubormay, faqat ko'rsatish

SOZLAMALAR (.env):

    ZAXIRA_BUCKET              majburiy — nusxalar uchun ALOHIDA R2 paqiri
    ZAXIRA_PAROL               majburiy — gpg shifrlash paroli (uzun bo'lsin)
    ZAXIRA_ACCESS_KEY_ID       ixtiyoriy — bo'sh bo'lsa media kaliti ishlatiladi
    ZAXIRA_SECRET_ACCESS_KEY   ixtiyoriy
    ZAXIRA_ENDPOINT_URL        ixtiyoriy — bo'sh bo'lsa media endpoint'i

TIKLASH (parolni so'raydi):

    gpg -d oqqushlar-2026-09-09-0300.dump.gpg > tiklash.dump
    pg_restore -d <baza> --clean --if-exists tiklash.dump
"""
import datetime
import logging
import os
import re
import subprocess
import tempfile
import threading

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

jurnal = logging.getLogger("taklif.zaxira")

# Fayl nomi: prefiks + sana. Sana nomdan o'qiladi, chunki R2'ning o'z
# "oxirgi o'zgarish" vaqtiga tayanish xavfli — nusxa ko'chirilganda u
# yangilanib ketadi va saqlash muddati noto'g'ri hisoblanadi.
PREFIKS = "zaxira/"
NOM_NAQSHI = re.compile(r"^zaxira/oqqushlar-(\d{4})-(\d{2})-(\d{2})-\d{4}\.dump\.gpg$")

# Saqlash siyosati. Oxirgi ikki hafta — har kuni; undan oldingi ikki oy —
# faqat yakshanbalar. Bu odatiy "kundalik + haftalik" naqsh: yaqin o'tmish
# batafsil, uzoq o'tmish siyrak.
KUNDALIK_SAQLASH_KUNI = 14
HAFTALIK_SAQLASH_KUNI = 56

# TAFTISH TOPILMASI (2026-09-14): yangi nusxa oldingi eng so'nggisidan shu
# nisbatdan KICHIKROQ chiqsa (masalan yarmidan ko'proq kichraysa), bu
# "texnik jihatdan muvaffaqiyatli, lekin mazmunan shubhali" holat deb
# hisoblanadi — pg_dump xatosiz tugashi mumkin, lekin baza kutilmaganda
# deyarli bo'shab qolgan bo'lsa (masalan noto'g'ri ulanish yoki adashib
# bosilgan ommaviy o'chirish), bu "hajm juda kichik" tekshiruvidan
# (mutlaq chegara — pastda) o'tib ketadi. Qarang: _hajm_pasayishini_tekshir.
HAJM_PASAYISH_CHEGARASI = 0.5


def saqlanadimi(sana, bugun):
    """Shu sanadagi nusxa saqlansinmi yoki o'chirilsinmi.

    Alohida funksiya — R2'ga ulanmasdan test qilish uchun. Qaror faqat
    ikkita sanaga bog'liq, boshqa hech narsaga emas.
    """
    yosh = (bugun - sana).days
    if yosh <= KUNDALIK_SAQLASH_KUNI:
        return True                       # oxirgi ikki hafta — hammasi
    if yosh <= HAFTALIK_SAQLASH_KUNI:
        return sana.weekday() == 6        # keyingi ikki oy — faqat yakshanba
    return False


class Command(BaseCommand):
    help = "Bazaning shifrlangan zaxira nusxasini olib, R2'ga yuboradi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sinov", action="store_true",
            help="Hech narsa yubormaydi va o'chirmaydi — faqat nima bo'lishini aytadi.",
        )
        parser.add_argument(
            "--royxat", action="store_true",
            help="R2'dagi mavjud nusxalar ro'yxatini ko'rsatadi.",
        )
        parser.add_argument(
            "--tekshir", action="store_true",
            help=(
                "Oxirgi nusxani yuklab olib, ochib, pg_restore bilan o'qib "
                "ko'radi. Zaxira BOR bo'lishi yetarli emas — u TIKLANADIGAN "
                "bo'lishi kerak, buni faqat sinab bilish mumkin."
            ),
        )

    # ---------- asosiy oqim ----------

    def handle(self, *args, **sozlamalar):
        try:
            if sozlamalar["royxat"]:
                return self._royxat()
            if sozlamalar["tekshir"]:
                return self._tekshir()
            return self._zaxira_ol(sinov=sozlamalar["sinov"])
        except CommandError:
            raise
        except Exception as xato:
            # Telegram xabarnomasi shu logerga ulangan (settings.LOGGING) —
            # ya'ni tunda taymer ishlamay qolsa, admin ertalab biladi.
            jurnal.error("Zaxira olishda xatolik: %s", xato, exc_info=True)
            raise CommandError(f"Zaxira olinmadi: {xato}") from xato

    def _zaxira_ol(self, sinov=False):
        parol = self._parol()
        paqir = self._paqir()
        nom = PREFIKS + "oqqushlar-{:%Y-%m-%d-%H%M}.dump.gpg".format(
            datetime.datetime.now()
        )

        if sinov:
            self.stdout.write(f"Sinov: {nom} yasalib, {paqir} paqiriga yuborilardi.")
            self._eskilarni_tozalash(paqir, sinov=True)
            return

        # Solishtirish uchun OLDINGI ro'yxat, yuborishdan OLDIN olinadi —
        # aks holda yangi nusxaning o'zi ro'yxatga kirib, "oldingi eng
        # so'nggisi" bilan o'zini solishtirib qo'yardi.
        oldingi_nusxalar = self._nusxalar(paqir)

        with tempfile.TemporaryDirectory(prefix="oqqushlar-zaxira-") as papka:
            yol = os.path.join(papka, "zaxira.gpg")
            hajm = self._dump_va_shifrla(yol, parol)
            self.stdout.write(f"Nusxa yasaldi: {self._olcham(hajm)}")
            self._hajm_pasayishini_tekshir(hajm, oldingi_nusxalar)
            self._yuborish(paqir, nom, yol, hajm)

        self.stdout.write(self.style.SUCCESS(f"Yuborildi: {paqir}/{nom}"))
        self._eskilarni_tozalash(paqir)

    # ---------- pg_dump | gpg ----------

    def _dump_va_shifrla(self, yol, parol):
        """pg_dump chiqishini to'g'ridan-to'g'ri gpg'ga uzatadi.

        Ochiq matn diskka yozilmaydi: ikkala jarayon quvur bilan ulanadi,
        faqat shifrlangan natija faylga tushadi.
        """
        baza = settings.DATABASES["default"]
        if "postgres" not in baza.get("ENGINE", ""):
            raise CommandError(
                "Bu buyruq faqat PostgreSQL uchun. Joriy ENGINE: "
                f"{baza.get('ENGINE')}"
            )

        muhit = os.environ.copy()
        if baza.get("PASSWORD"):
            muhit["PGPASSWORD"] = baza["PASSWORD"]

        dump_buyrugi = ["pg_dump", "--format=custom", "--no-owner", "--no-privileges"]
        if baza.get("HOST"):
            dump_buyrugi += ["--host", str(baza["HOST"])]
        if baza.get("PORT"):
            dump_buyrugi += ["--port", str(baza["PORT"])]
        if baza.get("USER"):
            dump_buyrugi += ["--username", str(baza["USER"])]
        dump_buyrugi.append(baza["NAME"])

        gpg_buyrugi = [
            "gpg", "--batch", "--yes", "--symmetric",
            "--cipher-algo", "AES256",
            "--passphrase-fd", "0",
            "--output", yol,
        ]

        # TAFTISH TOPILMASI (2026-09-14): ilgari har ikkala jarayonning
        # stderr'i FAQAT pastdagi ko'chirish sikli tugagach o'qilardi.
        # Operatsion tizimning quvur bufferi cheklangan (odatda ~64KB) —
        # agar pg_dump yoki gpg shu ko'chirish davomida ko'p miqdorda
        # ogohlantirish/xato yozib yuborsa (aynan xatolik yuz berganda bu
        # eng ehtimolli payt!), stderr bufferi to'lib, o'sha jarayon
        # yozishni davom ettira olmay TO'XTAB QOLARDI — asosiy oqim esa
        # hali stdout->stdin ko'chirish bilan band, stderr'ni o'qishga
        # yetib ulgurmagan bo'lardi. Ikkalasi bir-birini abadiy kutib
        # QOTIB QOLISHI (deadlock) mumkin edi. Endi ikkala stderr alohida
        # ipda (thread) ko'chirish bilan BIR VAQTDA to'liq o'qib olinadi.
        def _oqimni_toliq_oqi(oqim, natija):
            natija.append(oqim.read())

        with open(os.devnull, "wb") as bekor:
            dump = subprocess.Popen(
                dump_buyrugi, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=muhit
            )
            gpg = subprocess.Popen(
                gpg_buyrugi, stdin=subprocess.PIPE, stdout=bekor, stderr=subprocess.PIPE
            )

            dump_xato_natija = []
            gpg_xato_natija = []
            dump_stderr_ipi = threading.Thread(
                target=_oqimni_toliq_oqi, args=(dump.stderr, dump_xato_natija)
            )
            gpg_stderr_ipi = threading.Thread(
                target=_oqimni_toliq_oqi, args=(gpg.stderr, gpg_xato_natija)
            )
            dump_stderr_ipi.start()
            gpg_stderr_ipi.start()

            # Parolni birinchi qatorda beramiz, keyin dump oqimini uzatamiz.
            gpg.stdin.write((parol + "\n").encode())
            gpg.stdin.flush()
            for bolak in iter(lambda: dump.stdout.read(1024 * 256), b""):
                gpg.stdin.write(bolak)
            gpg.stdin.close()
            dump.stdout.close()

            gpg.wait()
            dump.wait()
            dump_stderr_ipi.join()
            gpg_stderr_ipi.join()
            dump_xato = dump_xato_natija[0]
            gpg_xato = gpg_xato_natija[0]

        if dump.returncode != 0:
            raise CommandError(f"pg_dump xatolik berdi: {dump_xato.decode(errors='replace')[:500]}")
        if gpg.returncode != 0:
            raise CommandError(f"gpg xatolik berdi: {gpg_xato.decode(errors='replace')[:500]}")

        hajm = os.path.getsize(yol)
        # Bo'sh yoki shubhali kichik fayl — bu ham nosozlik. Jim o'tkazib
        # yubormaymiz, aks holda "zaxira bor" degan yolg'on xotirjamlik
        # paydo bo'ladi.
        if hajm < 1024:
            raise CommandError(f"Zaxira fayli juda kichik ({hajm} bayt) — nosozlik.")
        return hajm

    def _hajm_pasayishini_tekshir(self, yangi_hajm, oldingi_nusxalar):
        """Yangi nusxa oldingi eng so'nggisidan shubhali darajada kichik
        bo'lsa, ogohlantiradi — lekin zaxira olishni TO'XTATMAYDI.

        ATAYLAB xato (CommandError) emas: baza haqiqatan kichraygan
        bo'lishi mumkin (masalan eski_chiqindilarni_tozalash ishlagandan
        keyin) — bunday holatda bitta kechalik zaxirani BUTUNLAY
        o'tkazib yuborish, shubhani sukut bilan o'tkazib yuborishdan
        battar bo'lardi. Shuning uchun faqat ERROR darajasida jurnalga
        (demak — settings.LOGGING orqali Telegram'ga ham) xabar beriladi,
        admin o'zi tekshirib ko'radi.
        """
        if not oldingi_nusxalar:
            return  # birinchi nusxa — solishtiradigan hech narsa yo'q
        _kalit, _sana, oldingi_hajm = oldingi_nusxalar[0]
        if oldingi_hajm <= 0:
            return
        nisbat = yangi_hajm / oldingi_hajm
        if nisbat < HAJM_PASAYISH_CHEGARASI:
            jurnal.error(
                "Zaxira hajmi shubhali darajada kichraydi: %s -> %s "
                "(oldingisining %.0f%%i) — baza kutilmaganda bo'shab "
                "qolgan bo'lishi mumkin, tekshiring.",
                self._olcham(oldingi_hajm), self._olcham(yangi_hajm),
                nisbat * 100,
            )

    # ---------- R2 ----------

    def _mijoz(self):
        import boto3

        return boto3.client(
            "s3",
            aws_access_key_id=(
                getattr(settings, "ZAXIRA_ACCESS_KEY_ID", "")
                or getattr(settings, "AWS_ACCESS_KEY_ID", "")
            ),
            aws_secret_access_key=(
                getattr(settings, "ZAXIRA_SECRET_ACCESS_KEY", "")
                or getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
            ),
            endpoint_url=(
                getattr(settings, "ZAXIRA_ENDPOINT_URL", "")
                or getattr(settings, "AWS_S3_ENDPOINT_URL", None)
            ),
            region_name=getattr(settings, "AWS_S3_REGION_NAME", None) or "auto",
        )

    def _yuborish(self, paqir, nom, yol, hajm):
        mijoz = self._mijoz()
        with open(yol, "rb") as fayl:
            mijoz.upload_fileobj(fayl, paqir, nom)
        # Yuborilganini TASDIQLAYMIZ. upload_fileobj jim tugashi mumkin,
        # lekin fayl yetib bormasligi ham mumkin — hajmni solishtiramiz.
        javob = mijoz.head_object(Bucket=paqir, Key=nom)
        if javob["ContentLength"] != hajm:
            # TAFTISH TOPILMASI (2026-09-14): ilgari bu yerda faqat xato
            # ko'tarilardi — R2'da NOMOS (qisqa/buzuq) fayl ABADIY qolib
            # ketardi. Keyingi safar --royxat/--tekshir buni "eng oxirgi
            # nusxa" deb noto'g'ri qabul qilishi (yoki hech bo'lmasa
            # bekorga joy egallashi) mumkin edi. Endi bunday holda nomos
            # fayl DARHOL R2'dan o'chiriladi — xato baribir ko'tariladi
            # (Telegram'ga xabar boradi), lekin R2'da faqat HAQIQIY
            # nusxalar qoladi.
            try:
                mijoz.delete_object(Bucket=paqir, Key=nom)
            except Exception:
                # taklif.zaxira logeri faqat ERROR darajasini Telegram'ga
                # yuboradi (settings.LOGGING) — bu ikkilamchi muvaffaqiyat-
                # sizlik ham ko'rinmasdan qolmasligi kerak.
                jurnal.error(
                    "Nomos yuklangan zaxira faylini R2'dan o'chirib bo'lmadi: "
                    "%s/%s", paqir, nom, exc_info=True,
                )
            raise CommandError(
                f"Yuborilgan fayl hajmi mos emas: {javob['ContentLength']} != "
                f"{hajm} — nomos fayl R2'dan o'chirishga urinildi."
            )

    def _nusxalar(self, paqir):
        """R2'dagi nusxalar: [(kalit, sana, hajm), ...] — yangisi birinchi."""
        mijoz = self._mijoz()
        topilgan = []
        belgi = None
        while True:
            qism = {"Bucket": paqir, "Prefix": PREFIKS}
            if belgi:
                qism["ContinuationToken"] = belgi
            javob = mijoz.list_objects_v2(**qism)
            for obyekt in javob.get("Contents", []):
                moslik = NOM_NAQSHI.match(obyekt["Key"])
                if moslik:
                    sana = datetime.date(*(int(q) for q in moslik.groups()))
                    topilgan.append((obyekt["Key"], sana, obyekt["Size"]))
            if not javob.get("IsTruncated"):
                break
            belgi = javob.get("NextContinuationToken")
        return sorted(topilgan, key=lambda q: q[0], reverse=True)

    # ---------- saqlash muddati ----------

    def _eskilarni_tozalash(self, paqir, sinov=False):
        bugun = datetime.date.today()
        ochiriladi = []
        for kalit, sana, _hajm in self._nusxalar(paqir):
            if not saqlanadimi(sana, bugun):
                ochiriladi.append(kalit)

        if not ochiriladi:
            self.stdout.write("Eski nusxa yo'q — hech narsa o'chirilmadi.")
            return
        if sinov:
            self.stdout.write(f"Sinov: {len(ochiriladi)} ta eski nusxa o'chirilardi.")
            return

        mijoz = self._mijoz()
        for kalit in ochiriladi:
            mijoz.delete_object(Bucket=paqir, Key=kalit)
        self.stdout.write(f"{len(ochiriladi)} ta eski nusxa o'chirildi.")

    # ---------- ro'yxat va tekshiruv ----------

    def _royxat(self):
        nusxalar = self._nusxalar(self._paqir())
        if not nusxalar:
            self.stdout.write(self.style.WARNING("Zaxira nusxa topilmadi."))
            return
        for kalit, sana, hajm in nusxalar:
            yosh = (datetime.date.today() - sana).days
            self.stdout.write(f"  {kalit}  {self._olcham(hajm):>10}  {yosh} kun oldin")
        self.stdout.write(f"\nJami: {len(nusxalar)} ta nusxa.")

    def _tekshir(self):
        """Oxirgi nusxani yuklab, ochib, o'qib ko'radi.

        Zaxira BOR bo'lishi hech narsani anglatmaydi — u TIKLANADIGAN
        bo'lishi kerak. Bu yerda haqiqiy tiklash qilinmaydi (bazaga
        tegilmaydi), lekin fayl ochilishi va pg_restore uning ichidagi
        jadvallar ro'yxatini o'qiy olishi tekshiriladi.
        """
        nusxalar = self._nusxalar(self._paqir())
        if not nusxalar:
            raise CommandError("Tekshirish uchun nusxa yo'q.")
        kalit, sana, hajm = nusxalar[0]
        self.stdout.write(f"Tekshirilmoqda: {kalit} ({self._olcham(hajm)})")

        with tempfile.TemporaryDirectory(prefix="oqqushlar-tekshir-") as papka:
            shifrli = os.path.join(papka, "z.gpg")
            ochiq = os.path.join(papka, "z.dump")
            self._mijoz().download_file(self._paqir(), kalit, shifrli)

            ochish = subprocess.run(
                ["gpg", "--batch", "--yes", "--decrypt", "--passphrase-fd", "0",
                 "--output", ochiq, shifrli],
                input=(self._parol() + "\n").encode(),
                capture_output=True,
            )
            if ochish.returncode != 0:
                raise CommandError(
                    "Faylni ochib bo'lmadi (parol noto'g'ri yoki fayl buzilgan): "
                    + ochish.stderr.decode(errors="replace")[:300]
                )

            royxat = subprocess.run(
                ["pg_restore", "--list", ochiq], capture_output=True
            )
            if royxat.returncode != 0:
                raise CommandError(
                    "pg_restore faylni o'qiy olmadi: "
                    + royxat.stderr.decode(errors="replace")[:300]
                )
            jadvallar = royxat.stdout.decode(errors="replace").count("TABLE DATA")

        self.stdout.write(self.style.SUCCESS(
            f"Nusxa o'qildi: {jadvallar} ta jadval ma'lumoti bor. Tiklanadi."
        ))

    # ---------- yordamchilar ----------

    def _paqir(self):
        paqir = getattr(settings, "ZAXIRA_BUCKET", "")
        if not paqir:
            raise CommandError(
                ".env faylida ZAXIRA_BUCKET ko'rsatilmagan. U media paqiridan "
                "ALOHIDA bo'lishi kerak — aks holda bitta xato ikkalasini "
                "birdan yo'q qiladi."
            )
        if paqir == getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
            raise CommandError(
                "ZAXIRA_BUCKET media paqiri bilan bir xil. Alohida paqir oching."
            )
        return paqir

    def _parol(self):
        parol = getattr(settings, "ZAXIRA_PAROL", "")
        if not parol:
            raise CommandError(
                ".env faylida ZAXIRA_PAROL ko'rsatilmagan. Bazada mijozlar va "
                "mehmonlarning shaxsiy ma'lumoti bor — shifrsiz saqlanmaydi."
            )
        if len(parol) < 20:
            raise CommandError("ZAXIRA_PAROL juda qisqa — kamida 20 belgi bo'lsin.")
        return parol

    @staticmethod
    def _olcham(baytlar):
        for birlik in ("B", "KB", "MB", "GB"):
            if baytlar < 1024 or birlik == "GB":
                return f"{baytlar:.0f} {birlik}" if birlik == "B" else f"{baytlar:.1f} {birlik}"
            baytlar /= 1024
