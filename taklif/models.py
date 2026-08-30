import secrets

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .validators import FaylHajmiValidator

# Mijoz o'zi yuklaydigan musiqa fayli uchun ruxsat etilgan kengaytmalar va
# eng katta hajm — cheklovsiz bo'lsa, mijoz istalgan turdagi va hajmdagi
# faylni "musiqa" sifatida yuklab, R2/S3 xarajatini yoki xotirani behuda
# oshirishi mumkin edi.
MUSIQA_KENGAYTMALARI = ["mp3", "wav", "ogg", "m4a", "aac"]
MUSIQA_MAKS_HAJM_MB = 15

# Mijoz o'zi yuklaydigan taklifnoma foto(lar)i uchun eng katta hajm. Turi
# ImageField orqali allaqachon tekshiriladi (haqiqiy rasm bo'lishi shart),
# lekin hajmga cheklov yo'q edi.
RASM_MAKS_HAJM_MB = 8

# Ikkinchi segment (mehmon slug'i) sifatida ishlatilmasligi kerak bo'lgan so'zlar,
# chunki "rsvp" va "yoqdi" allaqachon /<taklifnoma>/rsvp/, /<taklifnoma>/yoqdi/
# manzillari uchun band (urls.py'ga qarang).
MEHMON_REZERV_SLUGLAR = {"rsvp", "yoqdi"}

# Mijoz o'zi FAOLLASHTIRILGAN (to'langan) taklifnomasini o'chirganda, u darhol
# butunlay o'chirilmaydi — "chiqindilar"ga o'tkaziladi (Taklifnoma.faol=False,
# ochirilgan_vaqt=hozir) va shu muddat davomida admin panelidan tiklanishi
# mumkin. Muddat o'tgach, `eski_chiqindilarni_tozalash` boshqaruv buyrug'i
# (management command) ularni butunlay o'chiradi (bu buyruq VPS'da kunlik
# systemd timer orqali avtomatik ishga tushiriladi — README'ga qarang).
CHIQINDI_SAQLASH_KUNLARI = 30

# Marosim turlari — bozorda qabul qilingan nomlar asosida (Nikoh to'yi,
# Qiz uzatish, Sunnat to'yi, Beshik to'yi, Nahor oshi, Yubiley...).
# Eski kalitlar ("toy", "qizlar_bazmi") bazadagi mavjud yozuvlar buzilmasligi
# uchun saqlab qolindi — faqat ko'rinadigan nomlari yangilandi.
MAROSIM_TURLARI = [
    ("toy", _("Nikoh to'yi")),
    ("qizlar_bazmi", _("Qiz uzatish")),
    ("sunnat_toy", _("Sunnat to'yi")),
    ("beshik_toy", _("Beshik to'yi")),
    ("nahor_oshi", _("Nahor oshi")),
    ("yubiley", _("Yubiley")),
    ("tugilgan_kun", _("Tug'ilgan kun")),
    ("boshqa", _("Boshqa")),
]

# Bu marosim turlarida odatda ikkita ism (masalan kuyov-kelin) kerak bo'ladi;
# qolganlarida odatda bitta ism yetarli (forma shunga qarab moslashadi).
IKKI_ISMLI_MAROSIM_TURLARI = {"toy", "yubiley"}


SHABLON_TURKUMLARI = [
    ("zamonaviy", _("Zamonaviy")),
    ("milliy", _("Milliy")),
    ("bolalar", _("Bolalar")),
]


class Shablon(models.Model):
    """Taklifnoma dizayn shabloni (masalan: 'Registon', 'Suzani')."""

    nomi = models.CharField(max_length=100)
    kod = models.SlugField(unique=True, help_text="Shablon fayl nomi, masalan: registon")
    turkum = models.CharField(
        max_length=20,
        choices=SHABLON_TURKUMLARI,
        default="zamonaviy",
        help_text="Shablon tanlash sahifasida shu turkum ostida ko'rinadi",
    )
    rasm = models.ImageField(upload_to="shablonlar/", blank=True, null=True)
    narx = models.DecimalField(max_digits=10, decimal_places=0)
    ommaviy = models.BooleanField(
        default=True,
        help_text="False bo'lsa — individual/maxfiy shablon, faqat admin biriktira oladi",
    )

    class Meta:
        verbose_name = "Shablon"
        verbose_name_plural = "Shablonlar"
        ordering = ["nomi"]

    def __str__(self):
        return self.nomi


class MusiqaVariant(models.Model):
    """Admin oldindan yuklab qo'ygan tayyor fon musiqa variantlari.

    Mijoz taklifnoma yaratayotganda shulardan birini tanlashi yoki o'zi
    fayl yuklashi mumkin (Taklifnoma.musiqa). Bundan tashqari, sayt
    sahifalarida (bosh sahifa, yaratish oqimi) joriy interfeys tiliga mos
    variant fon musiqasi sifatida yangraydi — "til" maydoni shuning uchun.
    """

    nomi = models.CharField(max_length=100, help_text="Masalan: Lirik, Milliy, Zamonaviy")
    fayl = models.FileField(upload_to="musiqa_variantlari/")
    til = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default="uz",
        help_text=(
            "Sayt shu tilda ko'rilayotganda fon musiqasi sifatida yangraydi. "
            "Bitta tilda bir nechta variant bo'lsa, birinchisi olinadi."
        ),
    )
    faol = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tayyor musiqa varianti"
        verbose_name_plural = "Tayyor musiqa variantlari"
        ordering = ["nomi"]

    def __str__(self):
        return f"{self.nomi} ({self.get_til_display()})"


class NamunaRasm(models.Model):
    """Admin oldindan yuklab qo'ygan tayyor namuna rasm — musiqaga o'xshab.

    Mijoz taklifnoma yaratayotganda o'z fotosi bo'lmasa, shulardan birini
    (yoki ikkitasini) tanlashi mumkin; yoqmasa, o'z galereyasidan yuklaydi.
    Tanlangan rasmning nusxasi mijozning shaxsiy TaklifnomaRasm'i sifatida
    saqlanadi — kelajakda bu ro'yxat o'zgarsa ham, mijozning eski
    taklifnomasi buzilmaydi.
    """

    nomi = models.CharField(
        max_length=100, blank=True, help_text="Faqat admin uchun ichki nom (ixtiyoriy)"
    )
    rasm = models.ImageField(upload_to="namuna_rasmlar/")
    tartib = models.PositiveSmallIntegerField(default=0)
    faol = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Namuna rasm"
        verbose_name_plural = "Namuna rasmlar"
        ordering = ["tartib", "id"]

    def __str__(self):
        return self.nomi or f"Namuna rasm #{self.pk}"


class Taklifnoma(models.Model):
    """Bitta mijozga tegishli taklifnoma sahifasi."""

    marosim_turi = models.CharField(
        max_length=20, choices=MAROSIM_TURLARI, default="toy"
    )
    ism_1 = models.CharField(
        max_length=100, help_text="Masalan: kuyov, tug'ilgan kun egasi"
    )
    ism_2 = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ikkinchi ism (masalan: kelin). Kerak bo'lmasa bo'sh qoldiring",
    )
    slug = models.SlugField(
        unique=True, help_text="Ochiq link uchun, masalan: sardor-malika"
    )
    shablon = models.ForeignKey(
        Shablon, on_delete=models.PROTECT, related_name="taklifnomalar"
    )
    sana = models.DateTimeField(help_text="Tadbir sanasi va vaqti")
    toyxona = models.CharField(max_length=200, blank=True)
    manzil = models.CharField(max_length=300, blank=True)
    xarita_link = models.URLField(blank=True)
    musiqa = models.FileField(
        upload_to="musiqa/",
        blank=True,
        validators=[
            FileExtensionValidator(MUSIQA_KENGAYTMALARI),
            FaylHajmiValidator(MUSIQA_MAKS_HAJM_MB),
        ],
        help_text="O'zingiz yuklamoqchi bo'lsangiz (mp3/wav/ogg/m4a/aac, %(maks)s MB gacha)"
        % {"maks": MUSIQA_MAKS_HAJM_MB},
    )
    musiqa_variant = models.ForeignKey(
        MusiqaVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="taklifnomalar",
        help_text="Tayyor musiqalardan birini tanlash",
    )
    yoqdi_bosildi = models.BooleanField(
        default=False,
        editable=False,
        help_text="Mijoz 'Yoqdi' tugmasini bosganmi",
    )
    matn = models.TextField(blank=True, help_text="Qo'shimcha tabrik/taklif matni")
    kiyim_kodi = models.CharField(
        max_length=200, blank=True, help_text="Masalan: rasmiy, yorug' ranglar"
    )
    telegram_link = models.URLField(
        blank=True, help_text="Mehmonlar uchun Telegram guruh/kanal havolasi"
    )
    faol = models.BooleanField(default=True)
    korishlar = models.PositiveIntegerField(default=0)
    statistika_token = models.CharField(
        # DIQQAT: secrets.token_hex() argumentsiz chaqirilganda 32 BAYT
        # (ya'ni 64 ta hex belgi) qaytaradi — shuning uchun max_length aynan
        # 64 bo'lishi kerak. Bu SQLite'da xatolik bermas edi (SQLite
        # VARCHAR(n) uzunligini qat'iy tekshirmaydi), lekin PostgreSQL'da
        # "value too long for type character varying(32)" xatosi bilan
        # to'xtab qolar edi — buni real Postgres bazasiga migratsiya
        # qilishda aniqladim.
        max_length=64,
        default=secrets.token_hex,
        unique=True,
        editable=False,
    )
    sovga_karta = models.CharField(
        max_length=50, blank=True, help_text="Pul sovg'a uchun karta raqami"
    )
    tolangan = models.BooleanField(
        default=True,
        help_text="Self-service oqimi uchun: mijoz to'laguncha False bo'ladi",
    )
    yaratilgan = models.DateTimeField(auto_now_add=True)
    ochirilgan_vaqt = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        help_text=(
            "Mijoz o'zi o'chirgan FAOLLASHTIRILGAN (to'langan) taklifnoma shu "
            "vaqtda \"chiqindilar\"ga o'tkazilgan — faol=False qilingan, lekin "
            "ma'lumotlari (RSVP, rasmlar) darhol o'chirilmagan, "
            "CHIQINDI_SAQLASH_KUNLARI kun ichida admin panelidan tiklash mumkin. "
            "Bo'sh bo'lsa — hech qachon o'chirilmagan."
        ),
    )

    class Meta:
        verbose_name = "Taklifnoma"
        verbose_name_plural = "Taklifnomalar"
        ordering = ["-yaratilgan"]

    def __str__(self):
        return f"{self.sarlavha} ({self.slug})"

    def get_absolute_url(self):
        return reverse("taklif:korish", kwargs={"slug": self.slug})

    def get_statistika_url(self):
        return reverse("taklif:statistika", kwargs={"token": self.statistika_token})

    @property
    def sarlavha(self):
        if self.ism_2:
            return f"{self.ism_1} & {self.ism_2}"
        return self.ism_1

    @property
    def musiqa_manbai(self):
        """Ustuvorlik: mijoz o'zi yuklagan fayl, keyin tayyor variant."""
        if self.musiqa:
            return self.musiqa.url
        if self.musiqa_variant:
            return self.musiqa_variant.fayl.url
        return None

    @property
    def keladiganlar_soni(self):
        return sum(j.mehmonlar_soni for j in self.javoblar.filter(keladi=True))

    @property
    def kelmaydiganlar_soni(self):
        return self.javoblar.filter(keladi=False).count()


class Mehmon(models.Model):
    """Mijoz oldindan tayyorlaydigan, har bir mehmonga shaxsiy havola.

    Masalan: sayt.uz/ollomurod-kamola/aziz-oila/ — shu link orqali kirgan
    mehmon ismi bilan kutib olinadi va RSVP formasi oldindan to'ldirilgan bo'ladi.
    """

    taklifnoma = models.ForeignKey(
        Taklifnoma, related_name="mehmonlar", on_delete=models.CASCADE
    )
    ism = models.CharField(max_length=100, help_text="Masalan: Aziz oila, Malika")
    slug = models.SlugField(
        max_length=60,
        blank=True,
        help_text="Bo'sh qoldirsangiz, ismdan avtomatik yasaladi",
    )
    korilgan = models.BooleanField(default=False, editable=False)
    korilgan_vaqt = models.DateTimeField(null=True, blank=True, editable=False)
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mehmon (shaxsiy link)"
        verbose_name_plural = "Mehmonlar (shaxsiy linklar)"
        ordering = ["ism"]
        constraints = [
            models.UniqueConstraint(
                fields=["taklifnoma", "slug"], name="taklif_mehmon_slug_unique"
            )
        ]

    def __str__(self):
        return f"{self.ism} ({self.taklifnoma.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            # DIQQAT: "ism" 100 belgigacha bo'lishi mumkin, "slug" maydoni
            # esa faqat 60 belgi. slugify() uzunlikni cheklamaydi — shuning
            # uchun uzun ism (masalan butun oila nomi) kesilmasa, quyidagi
            # "-2", "-3" kabi raqam qo'shilganda maydon sig'imidan chiqib
            # ketishi mumkin edi. Bu SQLite'da sezilmas edi (u VARCHAR(n)
            # uzunligini qat'iy tekshirmaydi), lekin PostgreSQL'da "value
            # too long" xatosi bilan to'xtab qolardi — shu uchun "asosiy"
            # qismni suffiks uchun joy qoldirib, oldindan qisqartiramiz.
            max_uzunlik = self._meta.get_field("slug").max_length
            zaxira_joy = 10  # "-mehmon" yoki "-999" kabi qo'shimchalar uchun
            asosiy = slugify(self.ism)[: max_uzunlik - zaxira_joy] or "mehmon"
            if asosiy in MEHMON_REZERV_SLUGLAR:
                asosiy = f"{asosiy}-mehmon"
            slug = asosiy[:max_uzunlik]
            raqam = 1
            while (
                Mehmon.objects.filter(taklifnoma=self.taklifnoma, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                raqam += 1
                slug = f"{asosiy}-{raqam}"[:max_uzunlik]
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "taklif:mehmon_korish",
            kwargs={"slug": self.taklifnoma.slug, "mehmon_slug": self.slug},
        )


class RSVP(models.Model):
    """Mehmonning kelish-kelmasligi haqidagi javobi."""

    taklifnoma = models.ForeignKey(
        Taklifnoma, related_name="javoblar", on_delete=models.CASCADE
    )
    mehmon = models.ForeignKey(
        Mehmon,
        related_name="javoblar",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Agar mehmon shaxsiy link orqali kirgan bo'lsa, avtomatik bog'lanadi",
    )
    ism = models.CharField(max_length=100)
    keladi = models.BooleanField()
    mehmonlar_soni = models.PositiveSmallIntegerField(default=1)
    izoh = models.CharField(
        max_length=300, blank=True, help_text="Ixtiyoriy izoh (masalan: allergiya, maxsus talab)"
    )
    yaratilgan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "RSVP javobi"
        verbose_name_plural = "RSVP javoblari"
        ordering = ["-yaratilgan"]
        constraints = [
            # Shaxsiy link (mehmon) orqali RSVP yuborilganda — bitta mehmon
            # bitta taklifnomaga faqat BITTA javobga ega bo'lishi kerak (forma
            # qayta yuborilsa/yangilansa, eskisi ustiga yozilishi kerak, yangi
            # qator qo'shilmasligi kerak — aks holda mehmonlar soni bir necha
            # barobar oshib ketadi). Umumiy (shaxsiy linksiz, mehmon=NULL)
            # javoblarga bu cheklov ta'sir qilmaydi — SQLite ham, PostgreSQL
            # ham NULL qiymatlarni bir-biriga "teng" deb hisoblamaydi, shuning
            # uchun bir nechta mehmon=NULL yozuv bir xil taklifnoma uchun
            # erkin qo'shilishda davom etadi.
            models.UniqueConstraint(
                fields=["taklifnoma", "mehmon"], name="rsvp_taklifnoma_mehmon_bir_marta"
            ),
        ]

    def __str__(self):
        holat = "keladi" if self.keladi else "kelmaydi"
        return f"{self.ism} — {holat} ({self.taklifnoma.slug})"


class TaklifnomaRasm(models.Model):
    """Mijoz o'zi yuklaydigan taklifnoma fotogalereyasidagi bitta rasm."""

    taklifnoma = models.ForeignKey(
        Taklifnoma, related_name="rasmlar", on_delete=models.CASCADE
    )
    rasm = models.ImageField(
        upload_to="taklifnoma_rasmlar/",
        validators=[FaylHajmiValidator(RASM_MAKS_HAJM_MB)],
    )
    tartib = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Taklifnoma rasmi"
        verbose_name_plural = "Taklifnoma rasmlari"
        ordering = ["tartib", "id"]

    def __str__(self):
        return f"{self.taklifnoma.slug} — rasm #{self.pk}"


class SaytSozlamalari(models.Model):
    """Butun sayt uchun umumiy, admin panelidan o'zgartiriladigan sozlamalar.

    Faqat BITTA qator bo'lishi kerak (singleton) — shuning uchun saqlashda
    pk har doim 1 ga majburlanadi va o'chirish bloklangan. Bu server
    kodini/environment o'zgaruvchilarini qayta joylashtirmasdan (deploy
    qilmasdan) ba'zi qiymatlarni tez o'zgartirish imkonini beradi.
    """

    admin_telegram = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Mijoz \"Yoqdi, to'lov qilmoqchiman\" tugmasini bosganda "
            "yo'naltiriladigan Telegram username, @ belgisi bilan "
            "(masalan: @username). Bo'sh qoldirilsa, serverdagi standart "
            "qiymat (SAYT_ADMIN_TELEGRAM) ishlatiladi."
        ),
    )

    class Meta:
        verbose_name = "Sayt sozlamalari"
        verbose_name_plural = "Sayt sozlamalari"

    def __str__(self):
        return "Sayt sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Singleton — o'chirishga yo'l qo'ymaymiz.
        pass

    @classmethod
    def olish(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
