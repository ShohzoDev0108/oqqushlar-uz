from django import forms
from django.utils.translation import gettext_lazy as _

from .models import IKKI_ISMLI_MAROSIM_TURLARI, MAROSIM_TURLARI, MusiqaVariant, Taklifnoma

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
        empty_label=_("— tanlanmagan —"),
    )

    class Meta:
        model = Taklifnoma
        fields = [
            "marosim_turi",
            "ism_1",
            "ism_2",
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
        ]
        widgets = {
            "sana": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "matn": forms.Textarea(attrs={"rows": 3}),
            # Brauzerning fayl tanlash oynasida faqat audio fayllarni ko'rsatadi
            # (qulaylik uchun — asosiy himoya baribir modeldagi validatorlar,
            # bu yerdagi "accept" faqat UX, xavfsizlik uchun emas).
            "musiqa": forms.ClearableFileInput(attrs={"accept": "audio/*"}),
        }
        labels = {
            "ism_1": _("1-ism (masalan: kuyov, tug'ilgan kun egasi)"),
            "ism_2": _("2-ism (ixtiyoriy, masalan: kelin)"),
            "sana": _("Tadbir sanasi va vaqti"),
            "toyxona": _("To'yxona/manzil nomi"),
            "manzil": _("Manzil"),
            "xarita_link": _("Xarita havolasi (ixtiyoriy)"),
            "kiyim_kodi": _("Kiyinish kodi (ixtiyoriy)"),
            "musiqa": _("O'zingiz musiqa yuklash (ixtiyoriy)"),
            "matn": _("Qo'shimcha tabrik matni (ixtiyoriy)"),
            "sovga_karta": _("Sovg'a-pul uchun karta raqami (ixtiyoriy)"),
            "telegram_link": _("Mehmonlar uchun Telegram guruhi (ixtiyoriy)"),
        }
        help_texts = {
            "ism_1": _("Masalan: kuyov, tug'ilgan kun egasi"),
            "ism_2": _("Ikkinchi ism (masalan: kelin). Kerak bo'lmasa bo'sh qoldiring"),
            "sana": _("Tadbir sanasi va vaqti"),
            "kiyim_kodi": _("Masalan: rasmiy, yorug' ranglar"),
            "musiqa": _("O'zingiz yuklamoqchi bo'lsangiz"),
            "matn": _("Qo'shimcha tabrik/taklif matni"),
            "sovga_karta": _("Pul sovg'a uchun karta raqami"),
            "telegram_link": _("Mehmonlar uchun Telegram guruh/kanal havolasi"),
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
