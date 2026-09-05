import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import get_language, gettext_lazy as _, pgettext_lazy

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
# Fotiha to'yi, Qiz uzatish, Xatna to'yi, Beshik to'yi, Nahor oshi,
# Yubiley...). BU RO'YXAT Shablon.marosim_turlari, MusiqaVariant.marosim_turlari
# va NamunaRasm.marosim_turlari bilan ham baravar ishlatiladi (kategoriyalash
# loyihasi) — shu ro'yxatlar hech qachon bir-biridan uzilib qolmasligi
# uchun har doim FAQAT shu yerda, BITTA joyda o'zgartiriladi.
# Eski kalitlar ("toy", "qizlar_bazmi", "sunnat_toy") bazadagi mavjud
# yozuvlar buzilmasligi uchun saqlab qolindi — faqat ko'rinadigan nomlari
# yangilandi ("Sunnat to'yi" endi "Xatna to'yi" deb ko'rsatiladi).
MAROSIM_TURLARI = [
    ("toy", _("Nikoh to'yi")),
    ("fotiha_toy", _("Fotiha to'yi")),
    ("qizlar_bazmi", _("Qiz uzatish")),
    ("sunnat_toy", _("Xatna to'yi")),
    ("beshik_toy", _("Beshik to'yi")),
    ("nahor_oshi", _("Nahor oshi")),
    ("yubiley", _("Yubiley")),
    ("tugilgan_kun", _("Tug'ilgan kun")),
    ("boshqa", _("Boshqa")),
]

# Shablon tanlash sahifasida "Marosim turi" filtri barcha 8 turni bir xil
# darajadagi tugma sifatida ko'rsatsa — vizual jihatdan tig'iz/og'ir
# ko'rinadi. Shu sabab faqat eng ko'p tanlanadigan 4 tasi asosiy qatorda
# doim ko'rinadi, qolganlari "Yana" ochiladigan qatorida beriladi (nomi
# "Boshqa" emas — bu so'z Taklifnoma.marosim_turi'dagi "boshqa" qiymati
# bilan chalkashmasligi uchun ataylab boshqacha tanlandi). Ro'yxat
# MAROSIM_TURLARI bilan bir xil kalitlardan foydalanadi — shu yerda faqat
# GURUHLASH belgilanadi, nomlar yuqoridagi ro'yxatdan olinadi.
MAROSIM_ASOSIY_KALITLAR = ["toy", "fotiha_toy", "qizlar_bazmi", "sunnat_toy"]


def _marosim_turlari_maydoni():
    """Shablon/MusiqaVariant/NamunaRasm — bittasi bir nechta marosim turiga
    mos bo'lishi mumkin (masalan bitta dizayn ham Nikoh, ham Fotiha
    to'yiga mos) — shuning uchun BITTA emas, RO'YXAT sifatida saqlanadi.

    Django'da bunga alohida M2M jadval kerak bo'lardi, lekin ro'yxat kichik
    va o'zgarmas (yuqoridagi MAROSIM_TURLARI) bo'lgani uchun soddaroq yo'l
    tanlandi: bitta CharField'da vergul bilan ajratilgan kalitlar sifatida
    saqlanadi (masalan "toy,fotiha_toy,yubiley"), Python kodida va admin
    panelda esa `<nomi>_ro'yxati`/property orqali RO'YXAT ko'rinishida
    ishlatiladi (pastdagi har bir model shu naqshni takrorlaydi).
    """
    return models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "Qaysi marosim turlariga mos — bir nechtasini belgilash mumkin. "
            "Hech biri belgilanmasa, HECH BIR marosim filtrida aniq mos "
            "sifatida ko'rinmaydi (shablon tanlash sahifasida \"Barchasi\" "
            "tanlanganda esa baribir ko'rinadi)."
        ),
    )


def _turlar_royxati_dan_matn(qiymat):
    if isinstance(qiymat, str):
        return qiymat
    return ",".join(qiymat) if qiymat else ""


def _matndan_turlar_royxati(matn):
    return [k for k in (matn or "").split(",") if k]

# Bu marosim turlarida odatda ikkita ism (masalan kuyov-kelin) kerak bo'ladi;
# qolganlarida odatda bitta ism yetarli (forma shunga qarab moslashadi).
IKKI_ISMLI_MAROSIM_TURLARI = {"toy", "fotiha_toy", "yubiley"}

# Xatna to'yida bir nechta o'g'il bola bo'lishi mumkin (masalan aka-uka yoki
# amakivachchalarga birgalikda) — shu marosim turida UCHINCHI ism maydoni ham
# ko'rsatiladi (1-ism majburiy, 2- va 3-ism ixtiyoriy). Boshqa marosim
# turlarida uchinchi ism kerak bo'lmaydi.
UCHINCHI_ISM_MAROSIM_TURLARI = {"sunnat_toy"}

# Kun tartibi uchun NAMUNALAR.
#
# Mijozdan bo'sh jadvalni to'ldirishni so'rash — deyarli har doim bo'sh
# qoladigan maydon degani: odam "nima yozishim kerak?" degan savolda
# to'xtaydi. Shu sabab har bir marosim turi uchun O'ZBEK marosimlarida
# odatiy bo'lgan tayyor jadval bor: mijoz bir tugma bosadi, tayyor qatorlar
# chiqadi va u faqat vaqtini/nomini o'ziga moslab tahrirlaydi. Bu — bo'sh
# maydondan ko'ra ancha oson va natija ham ancha sifatliroq bo'ladi.
#
# Vaqtlar ATAYLAB "tadbir boshlanish vaqti"ga nisbatan emas, mutlaq
# qiymatda: mijozning ko'z oldida real soat turgani tushunarliroq, va u
# istagan qiymatga o'zgartira oladi.
MAROSIM_DASTUR_NAMUNALARI = {
    "toy": [
        {"vaqt": "17:30", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "18:00", "nom": _("Marosim boshlanishi"), "izoh": ""},
        {"vaqt": "19:00", "nom": _("Kelin-kuyov raqsi"), "izoh": ""},
        {"vaqt": "20:00", "nom": _("Tortni kesish"), "izoh": ""},
        {"vaqt": "22:00", "nom": _("Marosim yakuni"), "izoh": ""},
    ],
    "fotiha_toy": [
        {"vaqt": "11:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "11:30", "nom": _("Fotiha marosimi"), "izoh": ""},
        {"vaqt": "12:30", "nom": _("Ziyofat"), "izoh": ""},
    ],
    "qizlar_bazmi": [
        {"vaqt": "17:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "17:30", "nom": _("Marosim boshlanishi"), "izoh": ""},
        {"vaqt": "19:00", "nom": _("Oq yo'l tilaklari"), "izoh": ""},
        {"vaqt": "20:30", "nom": _("Qizni kuzatish"), "izoh": ""},
    ],
    "sunnat_toy": [
        {"vaqt": "10:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "11:00", "nom": _("Marosim boshlanishi"), "izoh": ""},
        {"vaqt": "12:00", "nom": _("Ziyofat"), "izoh": ""},
        {"vaqt": "14:00", "nom": _("Bolalar uchun o'yin-kulgi"), "izoh": ""},
    ],
    "beshik_toy": [
        {"vaqt": "11:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "11:30", "nom": _("Beshik marosimi"), "izoh": ""},
        {"vaqt": "12:30", "nom": _("Ziyofat"), "izoh": ""},
    ],
    "nahor_oshi": [
        {"vaqt": "06:30", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "07:00", "nom": _("Osh"), "izoh": ""},
        {"vaqt": "08:30", "nom": _("Duo va yakun"), "izoh": ""},
    ],
    "yubiley": [
        {"vaqt": "17:30", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "18:00", "nom": _("Tabriklar"), "izoh": ""},
        {"vaqt": "19:30", "nom": _("Ziyofat va konsert"), "izoh": ""},
        {"vaqt": "22:00", "nom": _("Marosim yakuni"), "izoh": ""},
    ],
    "tugilgan_kun": [
        {"vaqt": "15:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "15:30", "nom": _("O'yinlar va tabriklar"), "izoh": ""},
        {"vaqt": "16:30", "nom": _("Tortni kesish"), "izoh": ""},
    ],
    "boshqa": [
        {"vaqt": "18:00", "nom": _("Mehmonlarni qarshi olish"), "izoh": ""},
        {"vaqt": "18:30", "nom": _("Tadbir boshlanishi"), "izoh": ""},
        {"vaqt": "20:00", "nom": _("Ziyofat"), "izoh": ""},
    ],
}

# Bitta taklifnomada eng ko'pi bilan shuncha band bo'lishi mumkin. Cheklov
# ikki sababdan: (1) uzun jadval mehmonni o'qishdan charchatadi, (2) forma
# orqali kelayotgan JSON'ning hajmini oldindan chegaralab qo'yamiz.
DASTUR_MAKS_BAND = 10

# sunnat_toy_qoshma_sarlavha uchun: ismlarni "va" bilan bog'lab, oxirgisiga
# ko'plik+egalik qo'shimchasi ("...larning") qo'shish FAQAT o'zbekchada shu
# grammatik qolipda tabiiy eshitiladi ("Amir va Botirlarning xatna to'yi").
# Boshqa (hatto turkiy) tillarda ixtiyoriy ismga to'g'ri qo'shimcha
# qo'shish uchun unlilar uyg'unligini avtomatik hisoblash ishonchsiz
# bo'lgani uchun, qolgan barcha tillarda ism o'zgarishsiz qoladi — tarjima
# matnining o'zi ("Sünnet toýy: %(ismlar)s" kabi) grammatik jihatdan
# xavfsiz, "belgi: ismlar" qolipda tuziladi.
_SUNNAT_TOY_KOPLIK_QOSHIMCHA = {"uz": "lar"}


SHABLON_TURKUMLARI = [
    ("zamonaviy", _("Zamonaviy")),
    ("milliy", _("Milliy")),
    ("islomiy", _("Islomiy")),
]

# Millat/uslub — FAQAT turkum="milliy" bo'lganda mantiqiy (shablon tanlash
# sahifasida ham shu holatda ochiladi). "Islomiy" millat emas, alohida
# turkum sifatida yuqorida SHABLON_TURKUMLARI'da bor — shu sabab bu yerda
# takrorlanmaydi.
MILLATLAR = [
    ("ozbek", _("O'zbek")),
    ("qozoq", _("Qozoq")),
    ("qirgiz", _("Qirg'iz")),
    ("tojik", _("Tojik")),
    ("turkman", _("Turkman")),
    ("qoraqalpoq", _("Qoraqalpoq")),
    ("rus", _("Rus")),
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
    millat = models.CharField(
        max_length=20,
        choices=MILLATLAR,
        blank=True,
        default="",
        help_text=(
            "Faqat turkum \"Milliy\" bo'lganda mantiqiy — shablon tanlash "
            "sahifasida Milliy ichidagi millat filtrida shu bo'yicha ko'rinadi. "
            "Bo'sh qoldirilsa, millat filtridan qat'i nazar har doim ko'rinadi."
        ),
    )
    marosim_turlari_raw = _marosim_turlari_maydoni()
    rasm = models.ImageField(upload_to="shablonlar/", blank=True, null=True)
    narx = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        help_text="So'mda, masalan: 180000. Shablon tanlash va bosh sahifadagi narx shu yerdan olinadi.",
    )
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

    @property
    def marosim_turlari(self):
        return _matndan_turlar_royxati(self.marosim_turlari_raw)

    @marosim_turlari.setter
    def marosim_turlari(self, qiymat):
        self.marosim_turlari_raw = _turlar_royxati_dan_matn(qiymat)


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
    marosim_turlari_raw = _marosim_turlari_maydoni()

    class Meta:
        verbose_name = "Tayyor musiqa varianti"
        verbose_name_plural = "Tayyor musiqa variantlari"
        ordering = ["nomi"]

    def __str__(self):
        return f"{self.nomi} ({self.get_til_display()})"

    @property
    def marosim_turlari(self):
        return _matndan_turlar_royxati(self.marosim_turlari_raw)

    @marosim_turlari.setter
    def marosim_turlari(self, qiymat):
        self.marosim_turlari_raw = _turlar_royxati_dan_matn(qiymat)


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
    marosim_turlari_raw = _marosim_turlari_maydoni()

    class Meta:
        verbose_name = "Namuna rasm"
        verbose_name_plural = "Namuna rasmlar"
        ordering = ["tartib", "id"]

    def __str__(self):
        return self.nomi or f"Namuna rasm #{self.pk}"

    @property
    def marosim_turlari(self):
        return _matndan_turlar_royxati(self.marosim_turlari_raw)

    @marosim_turlari.setter
    def marosim_turlari(self, qiymat):
        self.marosim_turlari_raw = _turlar_royxati_dan_matn(qiymat)


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
    ism_3 = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Uchinchi ism — faqat xatna to'yida, agar bir nechta to'ybola "
            "bo'lsa. Kerak bo'lmasa bo'sh qoldiring"
        ),
    )
    # Marosim turi "Boshqa" tanlanganda, mijoz tadbir nomini o'zi yozib
    # kiritishi uchun (masalan "Do'kon ochilishi", "Bitiruv kechasi") —
    # to'ldirilsa, taklifnomada "Boshqa" so'zi o'rniga shu ko'rsatiladi.
    boshqa_tadbir_nomi = models.CharField(
        max_length=100,
        blank=True,
        help_text="Marosim turi \"Boshqa\" bo'lganda, tadbir nomini shu yerga yozing",
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
    matn = models.TextField(
        blank=True,
        help_text="Mehmonlarga atalgan so'z — taklifnomada ularga to'g'ridan-to'g'ri ko'rsatiladi",
    )
    kiyim_kodi = models.CharField(
        max_length=200, blank=True, help_text="Masalan: rasmiy, yorug' ranglar"
    )
    imzo = models.CharField(
        max_length=120,
        blank=True,
        help_text=(
            "Taklifnoma kim nomidan kelayotgani — masalan “Aliyevlar oilasi”. "
            "Bo'sh qoldirilsa, marosim egalarining ismlari ishlatiladi."
        ),
    )
    dastur = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Kun tartibi — [{'vaqt': '18:00', 'nom': 'Mehmonlarni qarshi olish', "
            "'izoh': ''}] ko'rinishidagi ro'yxat. Bo'sh bo'lsa, taklifnomada bu "
            "bo'lim umuman ko'rsatilmaydi."
        ),
    )
    telegram_link = models.URLField(
        blank=True, help_text="Mehmonlar uchun Telegram guruh/kanal havolasi"
    )
    faol = models.BooleanField(default=True)
    ommaviy_korsatishga_rozi = models.BooleanField(
        default=False,
        verbose_name="Bosh sahifada namuna sifatida ko'rsatishga rozilik",
        help_text=(
            "Yoqilsa, taklifnoma (ism, marosim turi, sana) sayt bosh "
            "sahifasidagi \"So'nggi taklifnomalar\" bo'limida boshqa "
            "mijozlarga namuna sifatida ko'rsatilishi mumkin. Standart "
            "holatda O'CHIQ — faqat mijoz o'zi aniq rozilik bildirsa yoqiladi."
        ),
    )
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
    def juftlik_marosimi(self):
        """Marosim juftlik (kelin-kuyov) haqidami?

        Shablonlardagi YURAK shakli — ochilish kartasining kesimi va
        kalendardagi tanlangan kun — shu xususiyat orqali boshqariladi.

        TAFTISH: ilgari yurak shakli hech qanday shartsiz, BARCHA marosim
        turlari uchun chizilardi. Bu sezilmagan, chunki dizaynlar faqat
        uchta turga (to'y, fotiha to'yi, yubiley) ruxsat etilgan edi.
        Lekin beshik to'yi, nahor oshi yoki xatna to'yiga taklifnoma
        ochgan mehmonga yurak shaklidagi karta ko'rsatish xato bo'lardi —
        aynan shu narsa qolgan marosim turlarini ochishga to'sqinlik
        qilayotgandi. Juftlik marosimlarining ro'yxati IKKI ISMLI
        marosimlar ro'yxati bilan bir xil: kelin-kuyov (yoki yubiley
        egalari) — ikki kishi.
        """
        return self.marosim_turi in IKKI_ISMLI_MAROSIM_TURLARI

    @property
    def sarlavha(self):
        qoshma = self.sunnat_toy_qoshma_sarlavha
        if qoshma:
            return qoshma
        if self.marosim_turi == "boshqa" and self.boshqa_tadbir_nomi:
            return self.boshqa_tadbir_nomi
        if self.ism_2:
            return f"{self.ism_1} & {self.ism_2}"
        return self.ism_1

    @property
    def sunnat_toy_qoshma_sarlavha(self):
        """Xatna to'yida (kod darajasida hali "sunnat_toy") 2 yoki 3 ta
        to'ybola ismi kiritilgan bo'lsa, grammatik jihatdan to'g'ri qo'shma
        sarlavha matnini qaytaradi: 2 ism uchun masalan "Amir va
        Botirlarning xatna to'yi", 3 ism uchun "Amir, Botir va
        Sardorlarning xatna to'ylari" (ko'plik — chunki har biriga alohida
        to'y bo'lishi mumkin). Faqat bitta ism kiritilgan bo'lsa yoki
        marosim turi xatna to'yi bo'lmasa — None (bunday holatda oddiy,
        umumiy sarlavha mantig'i ishlatiladi)."""
        if self.marosim_turi != "sunnat_toy":
            return None
        ismlar = [ism for ism in (self.ism_1, self.ism_2, self.ism_3) if ism]
        if len(ismlar) < 2:
            return None
        boshlari, oxirgisi = ismlar[:-1], ismlar[-1]
        til = (get_language() or "uz").split("-")[0]
        koplik = _SUNNAT_TOY_KOPLIK_QOSHIMCHA.get(til, "")
        oxirgisi_koplik = f"{oxirgisi}{koplik}" if koplik else oxirgisi
        biriktiruvchi = pgettext_lazy("ismlarni bog'lovchi so'z ('Amir VA Botir')", "va")
        ismlar_matni = f"{', '.join(boshlari)} {biriktiruvchi} {oxirgisi_koplik}"
        if len(ismlar) == 2:
            return _("%(ismlar)sning xatna to'yi") % {"ismlar": ismlar_matni}
        return _("%(ismlar)sning xatna to'ylari") % {"ismlar": ismlar_matni}

    @property
    def marosim_turi_matni(self):
        """Ro'yxatlarda/kichik sarlavhalarda ko'rsatiladigan marosim nomi —
        odatda marosim turining o'zi (masalan "Nikoh to'yi"), lekin marosim
        turi "Boshqa" bo'lib mijoz o'z tadbir nomini kiritgan bo'lsa, o'sha
        aniq nom ko'rsatiladi ("Boshqa" so'zi o'rniga)."""
        if self.marosim_turi == "boshqa" and self.boshqa_tadbir_nomi:
            return self.boshqa_tadbir_nomi
        return self.get_marosim_turi_display()

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
    ism = models.CharField(max_length=100, help_text="Masalan: Jasur Rahimov, Aliyevlar oilasi")
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
    # DIQQAT: "izoh"dan farqli — bu maydon (tasdiqlangach) taklifnoma
    # sahifasida HAMMAGA ochiq ko'rinadi. Shu sabab "izoh" bilan
    # aralashtirilmasligi kerak — u har doim faqat mezbonga (statistika
    # sahifasida) ko'rinadi.
    tilak = models.CharField(
        max_length=500,
        blank=True,
        help_text="Ixtiyoriy tabrik/tilak — avval faqat mezbonga ko'rinadi, mezbon tasdiqlagach taklifnoma sahifasida BARCHAGA ochiq bo'ladi.",
    )
    # Mehmon yozgan tilak DARHOL ommaga ochilmaydi — avval faqat mezbon
    # (statistika sahifasida) ko'radi va xohlasa "hammaga ko'rsatish"ni
    # bosadi. Sabab: bu havolani bilgan har kim (masalan sobiq sevgilisi)
    # yomon niyat bilan yozishi mumkin — moderatsiyasiz darhol ochiq
    # bo'lsa, buni mezbon oldindan to'xtata olmas edi.
    tilak_tasdiqlangan = models.BooleanField(
        default=False,
        help_text="Yoqilgan bo'lsa — tilak taklifnoma sahifasida hammaga ochiq. O'chiq bo'lsa — faqat mezbonga (statistika sahifasida) ko'rinadi.",
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

    telefon = models.CharField(
        max_length=40,
        blank=True,
        help_text=(
            "Bog'lanish uchun telefon raqami, masalan: +998 90 123 45 67. "
            "Bo'sh qoldirilsa, saytda telefon umuman ko'rsatilmaydi."
        ),
    )
    instagram = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Instagram username — @ bilan ham, to'liq havola bilan ham "
            "yozish mumkin (masalan: oqqushlar.uz). Bo'sh qoldirilsa "
            "ko'rsatilmaydi."
        ),
    )

    class Meta:
        verbose_name = "Sayt sozlamalari"
        verbose_name_plural = "Sayt sozlamalari"

    KESH_KALITI = "oq_sayt_sozlamalari"
    KESH_MUDDATI = 300  # soniya

    def __str__(self):
        return "Sayt sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        # Keshni darhol tozalaymiz — admin panelda o'zgartirilgan raqam
        # keyingi sahifadayoq ko'rinsin, 5 daqiqa kutmasin.
        cache.delete(self.KESH_KALITI)

    def delete(self, *args, **kwargs):
        # Singleton — o'chirishga yo'l qo'ymaymiz.
        pass

    @property
    def telefon_raqami(self):
        """"tel:" havolasi uchun — faqat raqamlar (va boshidagi "+").

        Ko'rinadigan matn chiroyli bo'lishi kerak ("+998 90 123 45 67"),
        havola esa bo'shliqsiz — aks holda ba'zi telefonlarda bosilganda
        raqam noto'g'ri terilardi."""
        if not self.telefon:
            return ""
        raqamlar = "".join(b for b in self.telefon if b.isdigit())
        return ("+" + raqamlar) if self.telefon.strip().startswith("+") else raqamlar

    @property
    def instagram_nomi(self):
        """Mijoz @ bilan ham, to'liq havola bilan ham yozishi mumkin —
        ikkalasidan ham toza username qaytariladi."""
        nom = (self.instagram or "").strip().rstrip("/")
        for old in ("https://", "http://", "www.", "instagram.com/"):
            if nom.startswith(old):
                nom = nom[len(old):]
        return nom.lstrip("@")

    @classmethod
    def olish(cls):
        """Sozlamalar deyarli hech qachon o'zgarmaydi, lekin endi HAR BIR
        sahifada o'qiladi (footerdagi aloqa kanallari uchun) — jumladan
        mehmonlar ochadigan taklifnomalarda ham. Shu sabab keshlanadi:
        aks holda har bir tashrif bitta ortiqcha bazaga so'rov qilardi."""
        obj = cache.get(cls.KESH_KALITI)
        if obj is None:
            obj, _ = cls.objects.get_or_create(pk=1)
            cache.set(cls.KESH_KALITI, obj, cls.KESH_MUDDATI)
        return obj
