import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# Ikkinchi segment (mehmon slug'i) sifatida ishlatilmasligi kerak bo'lgan so'zlar,
# chunki "rsvp" va "yoqdi" allaqachon /<taklifnoma>/rsvp/, /<taklifnoma>/yoqdi/
# manzillari uchun band (urls.py'ga qarang).
MEHMON_REZERV_SLUGLAR = {"rsvp", "yoqdi"}

MAROSIM_TURLARI = [
    ("toy", _("To'y")),
    ("qizlar_bazmi", _("Qizlar bazmi")),
    ("sunnat_toy", _("Sunnat to'yi")),
    ("yubiley", _("Yubiley")),
    ("tugilgan_kun", _("Tug'ilgan kun")),
    ("boshqa", _("Boshqa")),
]

# Bu marosim turlarida odatda ikkita ism (masalan kelin-kuyov) kerak bo'ladi;
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


class Taklifnoma(models.Model):
    """Bitta mijozga tegishli taklifnoma sahifasi."""

    marosim_turi = models.CharField(
        max_length=20, choices=MAROSIM_TURLARI, default="toy"
    )
    ism_1 = models.CharField(
        max_length=100, help_text="Masalan: kelin, tug'ilgan kun egasi"
    )
    ism_2 = models.CharField(
        max_length=100,
        blank=True,
        help_text="Ikkinchi ism (masalan: kuyov). Kerak bo'lmasa bo'sh qoldiring",
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
        upload_to="musiqa/", blank=True, help_text="O'zingiz yuklamoqchi bo'lsangiz"
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
        max_length=32, default=secrets.token_hex, unique=True, editable=False
    )
    sovga_karta = models.CharField(
        max_length=50, blank=True, help_text="Pul sovg'a uchun karta raqami"
    )
    tolangan = models.BooleanField(
        default=True,
        help_text="Self-service oqimi uchun: mijoz to'laguncha False bo'ladi",
    )
    yaratilgan = models.DateTimeField(auto_now_add=True)

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
            asosiy = slugify(self.ism) or "mehmon"
            if asosiy in MEHMON_REZERV_SLUGLAR:
                asosiy = f"{asosiy}-mehmon"
            slug = asosiy
            raqam = 1
            while (
                Mehmon.objects.filter(taklifnoma=self.taklifnoma, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                raqam += 1
                slug = f"{asosiy}-{raqam}"
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

    def __str__(self):
        holat = "keladi" if self.keladi else "kelmaydi"
        return f"{self.ism} — {holat} ({self.taklifnoma.slug})"


class TaklifnomaRasm(models.Model):
    """Mijoz o'zi yuklaydigan taklifnoma fotogalereyasidagi bitta rasm."""

    taklifnoma = models.ForeignKey(
        Taklifnoma, related_name="rasmlar", on_delete=models.CASCADE
    )
    rasm = models.ImageField(upload_to="taklifnoma_rasmlar/")
    tartib = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Taklifnoma rasmi"
        verbose_name_plural = "Taklifnoma rasmlari"
        ordering = ["tartib", "id"]

    def __str__(self):
        return f"{self.taklifnoma.slug} — rasm #{self.pk}"
