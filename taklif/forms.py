from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    IKKI_ISMLI_MAROSIM_TURLARI,
    MAROSIM_TURLARI,
    UCHINCHI_ISM_MAROSIM_TURLARI,
    MusiqaVariant,
    Taklifnoma,
)

# Bu so'zlar bilan tugaydigan/mos keladigan slug'larni taqiqlaymiz,
# chunki ular URL'da tizim sahifalari sifatida band (urls.py'ga qarang).
REZERV_SLUGLAR = {
    "yaratish",
    "statistika",
    "admin",
    "media",
    "static",
    "tayyor",
    "mening-taklifnomalarim",
}

# Taftish topilmasi: forma har doim "1-ism (masalan: kuyov, tug'ilgan kun
# egasi)" kabi BARCHA marosim turlari uchun umumlashtirilgan yorliq
# ko'rsatardi — masalan xatna to'yi tanlansa ham "kuyov" so'zi ko'rinib
# turardi, bu mijozni chalg'itardi. Endi har bir marosim turi UCHUN alohida
# yorliq + real (aylanma bo'lmagan) na'munaviy ism beriladi — forma
# yuklanganda standart marosim turi ("toy") uchun serverda, marosim turi
# almashtirilganda esa (yaratish.html'dagi JS orqali) mijoz tomonida
# qo'llaniladi.
MAROSIM_MAYDON_MATNLARI = {
    "toy": {
        "ism_1_yorliq": _("Kuyov ismi"),
        "ism_1_namuna": _("Masalan: Sardor"),
        "ism_2_yorliq": _("Kelin ismi"),
        "ism_2_namuna": _("Masalan: Malika"),
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "fotiha_toy": {
        "ism_1_yorliq": _("Yigit ismi"),
        "ism_1_namuna": _("Masalan: Sardor"),
        "ism_2_yorliq": _("Qiz ismi"),
        "ism_2_namuna": _("Masalan: Malika"),
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "qizlar_bazmi": {
        "ism_1_yorliq": _("Kelinchakning ismi"),
        "ism_1_namuna": _("Masalan: Nilufar"),
        "ism_2_yorliq": _("2-ism"),
        "ism_2_namuna": "",
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "sunnat_toy": {
        "ism_1_yorliq": _("To'ybolaning ismi"),
        "ism_1_namuna": _("Masalan: Amir"),
        "ism_2_yorliq": _("2-to'ybolaning ismi (ixtiyoriy)"),
        "ism_2_namuna": _("Masalan: Botir"),
        "ism_3_yorliq": _("3-to'ybolaning ismi (ixtiyoriy)"),
        "ism_3_namuna": _("Masalan: Sardor"),
    },
    "beshik_toy": {
        "ism_1_yorliq": _("Chaqaloqning ismi"),
        "ism_1_namuna": _("Masalan: Amina"),
        "ism_2_yorliq": _("2-ism"),
        "ism_2_namuna": "",
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "nahor_oshi": {
        "ism_1_yorliq": _("Tadbir egasining ismi"),
        "ism_1_namuna": _("Masalan: Bobur"),
        "ism_2_yorliq": _("2-ism"),
        "ism_2_namuna": "",
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "yubiley": {
        "ism_1_yorliq": _("Yubiley egasining ismi"),
        "ism_1_namuna": _("Masalan: Otabek"),
        "ism_2_yorliq": _("Ikkinchi ism (ikkoviga bag'ishlangan bo'lsa)"),
        "ism_2_namuna": _("Masalan: Dilnoza"),
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "tugilgan_kun": {
        "ism_1_yorliq": _("Tug'ilgan kun egasining ismi"),
        "ism_1_namuna": _("Masalan: Sevinch"),
        "ism_2_yorliq": _("2-ism"),
        "ism_2_namuna": "",
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
    "boshqa": {
        "ism_1_yorliq": _("Asosiy ism"),
        "ism_1_namuna": _("Masalan: Jahongir"),
        "ism_2_yorliq": _("Qo'shimcha ism (ixtiyoriy)"),
        "ism_2_namuna": "",
        "ism_3_yorliq": "",
        "ism_3_namuna": "",
    },
}

# Standart (sahifa birinchi ochilganda, hali JS ishlamasdan turib serverda
# ko'rsatiladigan) marosim turi — Taklifnoma.marosim_turi'ning model
# darajasidagi standart qiymati bilan bir xil bo'lishi shart.
STANDART_MAROSIM_TURI = "toy"

# Yaratish formasidagi o'zimizning sana+soat tanlagichimiz uchun — Yanvardan
# Dekabrgacha, tartib bilan (JS shu ro'yxatdan oy raqami bo'yicha oladi).
# DIQQAT: bu Django'ning o'z ichki (django/conf/locale/...) oy nomlari
# tarjimasidan emas — chunki bizning ba'zi tillarimiz (masalan qoraqalpoq,
# turkman) Django'ning o'zida rasman qo'llab-quvvatlanmaydi. Shu sababli
# loyihaning O'Z tarjima katalogi orqali (build_admin_uz_locale.py kabi
# emas, oddiy {% trans %} orqali) barcha 8 tilga tarjima qilinadi.
OY_NOMLARI = [
    _("Yanvar"), _("Fevral"), _("Mart"), _("Aprel"), _("May"), _("Iyun"),
    _("Iyul"), _("Avgust"), _("Sentyabr"), _("Oktyabr"), _("Noyabr"), _("Dekabr"),
]


class TaklifnomaYaratishForm(forms.ModelForm):
    """Mijoz o'zi to'ldiradigan taklifnoma yaratish formasi (self-service).

    E'tibor bering: "manzil (link)" mijozdan SO'RALMAYDI — ko'pchilik mijoz
    bu texnik tushunchani tushunmaydi. Havola ism_1/ism_2'dan avtomatik,
    orqa fonda (views.py'dagi yaratish() funksiyasida) yasaladi; mijoz uni
    faqat tayyor bo'lgach, natija sifatida ko'radi.
    """

    marosim_turi = forms.ChoiceField(
        label=_("Marosim turi"),
        choices=MAROSIM_TURLARI,
        widget=forms.Select(attrs={"id": "id_marosim_turi"}),
    )
    musiqa_variant = forms.ModelChoiceField(
        label=_("Tayyor musiqalardan tanlash (ixtiyoriy)"),
        queryset=MusiqaVariant.objects.filter(faol=True),
        required=False,
        empty_label=_("Tanlanmagan"),
    )

    class Meta:
        model = Taklifnoma
        fields = [
            "marosim_turi",
            "ism_1",
            "ism_2",
            "ism_3",
            "boshqa_tadbir_nomi",
            "sana",
            "toyxona",
            "manzil",
            "xarita_link",
            "kiyim_kodi",
            "musiqa_variant",
            "musiqa",
            "matn",
            "sovga_karta",
            "telegram_link",
            "ommaviy_korsatishga_rozi",
        ]
        widgets = {
            # DIQQAT: "sana" uchun standart <input type="datetime-local">
            # endi ishlatilmaydi — brauzer/qurilmaga qarab ko'rinishi juda
            # xilma-xil va sayt tiliga mos kelmas edi (doim qurilma tiliga
            # qarardi). O'rniga yaratish.html'da o'zimizning, sayt tiliga
            # to'liq mos kalendar+soat tanlagichimiz ishlatiladi — bu yerda
            # shunchaki oddiy yashirin matn maydoni sifatida qoldiriladi,
            # qiymatini o'sha JS to'ldiradi ("YYYY-MM-DDTHH:MM" formatida).
            "sana": forms.TextInput(
                attrs={"type": "hidden", "id": "id_sana"}
            ),
            "ism_1": forms.TextInput(attrs={"placeholder": _("Masalan: Sardor")}),
            "ism_2": forms.TextInput(attrs={"placeholder": _("Masalan: Malika")}),
            "ism_3": forms.TextInput(attrs={"placeholder": _("Masalan: Sardor")}),
            "boshqa_tadbir_nomi": forms.TextInput(
                attrs={"placeholder": _("Masalan: Do'kon ochilishi, Bitiruv kechasi")}
            ),
            "toyxona": forms.TextInput(
                attrs={"placeholder": _("Masalan: “Poytaxt” to'yxonasi")}
            ),
            "manzil": forms.TextInput(
                attrs={
                    "placeholder": _(
                        "Masalan: Toshkent sh., Chilonzor tumani, Bunyodkor ko'chasi 12"
                    )
                }
            ),
            "xarita_link": forms.URLInput(
                attrs={"placeholder": "https://yandex.uz/maps/..."}
            ),
            "kiyim_kodi": forms.TextInput(
                attrs={"placeholder": _("Masalan: rasmiy kiyim, och ranglar")}
            ),
            "matn": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _(
                        "Masalan: Sizlarsiz bu kun to'liq bo'lmaydi — quvonchimizga "
                        "sherik bo'lishingizni astoydil kutamiz"
                    ),
                }
            ),
            "sovga_karta": forms.TextInput(
                attrs={"placeholder": "8600 1234 5678 9012"}
            ),
            "telegram_link": forms.URLInput(
                attrs={"placeholder": "https://t.me/oilaviy_toy"}
            ),
            # Brauzerning fayl tanlash oynasida faqat audio fayllarni ko'rsatadi
            # (qulaylik uchun — asosiy himoya baribir modeldagi validatorlar,
            # bu yerdagi "accept" faqat UX, xavfsizlik uchun emas).
            "musiqa": forms.ClearableFileInput(attrs={"accept": "audio/*"}),
        }
        labels = {
            # Standart holat — "toy" (nikoh to'yi) uchun; boshqa marosim
            # turi tanlansa, yaratish.html'dagi JS bu yorliqlarni
            # MAROSIM_MAYDON_MATNLARI asosida darhol almashtiradi.
            "ism_1": MAROSIM_MAYDON_MATNLARI[STANDART_MAROSIM_TURI]["ism_1_yorliq"],
            "ism_2": MAROSIM_MAYDON_MATNLARI[STANDART_MAROSIM_TURI]["ism_2_yorliq"],
            "ism_3": MAROSIM_MAYDON_MATNLARI[STANDART_MAROSIM_TURI]["ism_3_yorliq"],
            "boshqa_tadbir_nomi": _("Tadbir nomi"),
            "sana": _("Tadbir sanasi va vaqti"),
            "toyxona": _("To'yxona/manzil nomi"),
            "manzil": _("Manzil"),
            "xarita_link": _("Xarita havolasi (ixtiyoriy)"),
            "kiyim_kodi": _("Kiyinish kodi (ixtiyoriy)"),
            "musiqa": _("O'zingiz musiqa yuklash (ixtiyoriy)"),
            "matn": _("Mehmonlarga atalgan so'zingiz (ixtiyoriy)"),
            "sovga_karta": _("Sovg'a-pul uchun karta raqami (ixtiyoriy)"),
            "telegram_link": _("Mehmonlar uchun Telegram guruhi (ixtiyoriy)"),
            "ommaviy_korsatishga_rozi": _(
                "Taklifnomangiz sayt bosh sahifasida namuna sifatida "
                "boshqa mijozlarga ko'rsatilishiga rozimisiz?"
            ),
        }
        help_texts = {
            # DIQQAT: quyidagi bo'sh qatorlar ataylab shunday — bu maydonlar
            # modelning o'zida (models.py) help_text bilan e'lon qilingan
            # (masalan admin panelida foydali bo'lishi uchun), lekin BU
            # formada endi har biri o'zining placeholder'i (real na'muna
            # matni) orqali ko'rsatiladi — ikkalasi birga chiqsa, bir xil
            # fikr ikki marta takrorlanib, forma "gavjum" ko'rinar edi.
            "ism_1": "",
            "ism_2": "",
            "ism_3": "",
            "boshqa_tadbir_nomi": _(
                "Marosim turini ro'yxatda topa olmasangiz shu yerga o'zingiz yozing."
            ),
            "kiyim_kodi": "",
            "matn": _("Taklifnomada mehmonlarga to'g'ridan-to'g'ri shu matn ko'rsatiladi."),
            "sovga_karta": "",
            "telegram_link": "",
            "musiqa": _("O'zingiz yuklamoqchi bo'lsangiz"),
            "ommaviy_korsatishga_rozi": _(
                "Ixtiyoriy. Belgilamasangiz ham taklifnomangiz odatdagidek "
                "ishlayveradi — bu faqat bosh sahifadagi namunalar ro'yxatiga tegishli."
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        marosim_turi = cleaned_data.get("marosim_turi")
        ism_2 = cleaned_data.get("ism_2")
        if marosim_turi in IKKI_ISMLI_MAROSIM_TURLARI and not ism_2:
            self.add_error(
                "ism_2",
                _("Bu marosim turi uchun ikkinchi ismni ham kiriting."),
            )
        return cleaned_data
