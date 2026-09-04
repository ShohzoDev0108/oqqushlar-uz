from django import forms
from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import (
    RSVP,
    MAROSIM_TURLARI,
    Mehmon,
    MusiqaVariant,
    NamunaRasm,
    SaytSozlamalari,
    Shablon,
    Taklifnoma,
    TaklifnomaRasm,
)


class MarosimTurlariFormMixin(forms.ModelForm):
    """Shablon/MusiqaVariant/NamunaRasm — bir nechta marosim turini
    belgilash uchun umumiy forma qismi (marosim_turlari_raw'ni checkbox
    ro'yxati sifatida ko'rsatadi, saqlashda qaytadan vergul bilan
    ajratilgan matnga aylantiradi).

    Ro'yxatda "Boshqa" ham bor: shablon tanlash sahifasida mijoz uni
    tanlay oladi (o'z nomli tadbir uchun — masalan "11-sinf
    o'quvchilari"), shuning uchun dizayn/musiqa/rasmni unga ham moslash
    imkoni bo'lishi kerak. Aks holda "Boshqa"ni tanlagan mijoz doim
    bo'sh ro'yxatga tushib qolardi.
    """

    marosim_turlari = forms.MultipleChoiceField(
        choices=list(MAROSIM_TURLARI),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Marosim turlari",
        help_text=(
            "Qaysi marosim turlariga mos — bir nechtasini belgilash mumkin. "
            "Hech biri belgilanmasa, hech bir aniq marosim filtrida "
            "ko'rinmaydi."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["marosim_turlari"].initial = self.instance.marosim_turlari

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.marosim_turlari = self.cleaned_data["marosim_turlari"]
        if commit:
            instance.save()
        return instance

# Taftish topilmasi: admin panel standart Django nomlanishida edi
# ("Django administration") — endi sayt nomiga mos (logotip va ranglar
# uchun qarang: templates/admin/base_site.html va
# taklif/static/taklif/admin/oqqushlar_admin.css).
admin.site.site_header = "Oqqushlar — boshqaruv paneli"
admin.site.site_title = "Oqqushlar admin"
admin.site.index_title = "Boshqaruv paneli"


class RSVPInline(admin.TabularInline):
    model = RSVP
    extra = 0
    readonly_fields = ("yaratilgan",)
    fields = ("ism", "keladi", "mehmonlar_soni", "izoh", "tilak", "tilak_tasdiqlangan", "mehmon", "yaratilgan")


class TaklifnomaRasmInline(admin.TabularInline):
    model = TaklifnomaRasm
    extra = 0
    fields = ("rasm", "tartib")


class MehmonInline(admin.TabularInline):
    model = Mehmon
    extra = 3
    fields = ("ism", "slug", "link_korsatish", "korilgan")
    readonly_fields = ("link_korsatish", "korilgan")

    @admin.display(description="Shaxsiy link")
    def link_korsatish(self, obj):
        if obj.pk:
            return obj.get_absolute_url()
        return "(saqlangach ko'rinadi)"


class ShablonAdminForm(MarosimTurlariFormMixin):
    class Meta:
        model = Shablon
        fields = "__all__"


@admin.register(Shablon)
class ShablonAdmin(admin.ModelAdmin):
    # "narx", "turkum", "millat" — list_editable: ro'yxatdagi har bir
    # shablonni alohida sahifaga kirmasdan, to'g'ridan-to'g'ri shu yerda
    # belgilash mumkin (o'zgartirib, pastdagi "Saqlash" tugmasini bosish
    # kifoya). "Marosim turlari" endi bir nechta qiymat qabul qilgani
    # uchun (checkbox ro'yxati) list_editable'da emas, faqat to'liq
    # o'zgartirish sahifasida ko'rinadi.
    form = ShablonAdminForm
    list_display = ("nomi", "kod", "turkum", "millat", "marosim_turlari_korsatish", "narx", "ommaviy")
    list_editable = ("turkum", "millat", "narx")
    list_filter = ("turkum", "millat", "ommaviy")
    search_fields = ("nomi", "kod")
    prepopulated_fields = {"kod": ("nomi",)}

    @admin.display(description="Marosim turlari")
    def marosim_turlari_korsatish(self, obj):
        nomlar = dict(MAROSIM_TURLARI)
        return ", ".join(str(nomlar.get(k, k)) for k in obj.marosim_turlari) or "—"


class MusiqaVariantAdminForm(MarosimTurlariFormMixin):
    class Meta:
        model = MusiqaVariant
        fields = "__all__"


@admin.register(MusiqaVariant)
class MusiqaVariantAdmin(admin.ModelAdmin):
    form = MusiqaVariantAdminForm
    list_display = ("nomi", "til", "marosim_turlari_korsatish", "faol")
    list_filter = ("til", "faol")
    search_fields = ("nomi",)

    @admin.display(description="Marosim turlari")
    def marosim_turlari_korsatish(self, obj):
        nomlar = dict(MAROSIM_TURLARI)
        return ", ".join(str(nomlar.get(k, k)) for k in obj.marosim_turlari) or "—"


class NamunaRasmAdminForm(MarosimTurlariFormMixin):
    class Meta:
        model = NamunaRasm
        fields = "__all__"


@admin.register(NamunaRasm)
class NamunaRasmAdmin(admin.ModelAdmin):
    form = NamunaRasmAdminForm
    list_display = ("__str__", "tartib", "marosim_turlari_korsatish", "faol")
    list_filter = ("faol",)
    search_fields = ("nomi",)

    @admin.display(description="Marosim turlari")
    def marosim_turlari_korsatish(self, obj):
        nomlar = dict(MAROSIM_TURLARI)
        return ", ".join(str(nomlar.get(k, k)) for k in obj.marosim_turlari) or "—"


@admin.register(Taklifnoma)
class TaklifnomaAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("taklif/admin/taklifnoma_royxat.css",)}

    list_display = (
        "belgi",
        "marosim_turi",
        "sana",
        "shablon",
        "faol",
        "tolangan",
        "chiqindida",
        "yoqdi_bosildi",
        "korishlar",
        "keladiganlar_soni",
        "statistika_link",
    )
    # "tolangan" (to'lov tasdiqlangani — taklifnomani mehmonlarga ochadi) va
    # "faol"ni ro'yxatning o'zidan, alohida sahifaga kirmasdan belgilash
    # mumkin bo'lsin — bu aynan to'lovni tasdiqlashda kundalik ishlatiladigan
    # amal, shuning uchun har safar "O'zgartirish"ga kirish shart emas.
    list_editable = ("faol", "tolangan")
    list_filter = (
        "faol", "tolangan", "marosim_turi", "yoqdi_bosildi", "shablon",
        ("ochirilgan_vaqt", admin.EmptyFieldListFilter),
    )
    search_fields = ("ism_1", "ism_2", "ism_3", "boshqa_tadbir_nomi", "slug")
    prepopulated_fields = {"slug": ("ism_1", "ism_2", "ism_3")}
    readonly_fields = (
        "statistika_token", "korishlar", "yaratilgan", "statistika_link", "yoqdi_bosildi",
        "ochirilgan_vaqt",
    )
    inlines = [MehmonInline, TaklifnomaRasmInline, RSVPInline]
    actions = ["chiqindidan_tiklash"]
    fieldsets = (
        ("Asosiy ma'lumot", {
            "fields": (
                "marosim_turi", "ism_1", "ism_2", "ism_3", "boshqa_tadbir_nomi",
                "slug", "shablon", "sana",
            )
        }),
        ("Manzil va qo'shimcha", {
            "fields": (
                "toyxona", "manzil", "xarita_link", "kiyim_kodi",
                "musiqa_variant", "musiqa", "matn", "imzo", "dastur",
                "sovga_karta", "telegram_link",
            )
        }),
        ("Holat", {
            "fields": (
                "faol", "tolangan", "yoqdi_bosildi", "korishlar",
                "statistika_token", "statistika_link", "yaratilgan", "ochirilgan_vaqt",
            )
        }),
    )

    @admin.display(description="Taklifnoma")
    def belgi(self, obj):
        # Taftish topilmasi: standart __str__ ustuni kengligi belgilanmagani
        # uchun har bir qator 3-4 satrga bo'linib, ro'yxatni haddan tashqari
        # uzun va ko'zdan kechirish qiyin qilib qo'yardi. Endi bitta qatorga
        # sig'adigan qisqa matn ko'rsatiladi, to'liq nom esa hover paytida
        # title sifatida chiqadi (CSS: taklifnoma_royxat.css).
        matn = str(obj)
        return format_html('<span title="{}">{}</span>', matn, matn)

    @admin.display(description="Statistika linki")
    def statistika_link(self, obj):
        if obj.pk:
            return obj.get_statistika_url()
        return "-"

    @admin.display(description="Chiqindida", boolean=True)
    def chiqindida(self, obj):
        return obj.ochirilgan_vaqt is not None

    @admin.action(description="Tanlanganlarni chiqindidan tiklash (faol qilish)")
    def chiqindidan_tiklash(self, request, queryset):
        yangilandi = queryset.filter(ochirilgan_vaqt__isnull=False).update(
            faol=True, ochirilgan_vaqt=None
        )
        self.message_user(request, f"{yangilandi} ta taklifnoma chiqindidan tiklandi.")


@admin.register(Mehmon)
class MehmonAdmin(admin.ModelAdmin):
    list_display = ("ism", "taklifnoma", "slug", "korilgan", "korilgan_vaqt")
    list_filter = ("korilgan",)
    search_fields = ("ism", "taklifnoma__slug", "taklifnoma__ism_1", "taklifnoma__ism_2")
    readonly_fields = ("korilgan", "korilgan_vaqt", "yaratilgan")


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = (
        "ism", "taklifnoma", "mehmon", "keladi", "mehmonlar_soni", "tilak",
        "tilak_tasdiqlangan", "yaratilgan",
    )
    # "tilak_tasdiqlangan" ro'yxatning o'zidan yoqilsa/o'chirilsa bo'ladi —
    # mijoz telefon orqali "tilaklarim ko'rinmayapti" desa, admin bu yerdan
    # tezda tasdiqlab qo'ya oladi (statistika sahifasidagi tugma bilan bir xil amal).
    list_editable = ("tilak_tasdiqlangan",)
    list_filter = ("keladi", "tilak_tasdiqlangan")
    search_fields = ("ism", "izoh", "tilak", "taklifnoma__slug", "taklifnoma__ism_1", "taklifnoma__ism_2")


@admin.register(SaytSozlamalari)
class SaytSozlamalariAdmin(admin.ModelAdmin):
    """Singleton — ro'yxatda bitta yozuv, yangi qo'shib yoki o'chirib bo'lmaydi."""

    fields = ("admin_telegram",)

    def has_add_permission(self, request):
        # Agar allaqachon bitta yozuv bo'lsa, yana qo'shishga ruxsat bermaymiz.
        return not SaytSozlamalari.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Ro'yxat sahifasiga kirganda to'g'ridan-to'g'ri yagona yozuvni
        # tahrirlash sahifasiga yo'naltiramiz — foydalanuvchi ro'yxatdan
        # qidirib o'tirmasin.
        sozlama = SaytSozlamalari.olish()
        return redirect("admin:taklif_saytsozlamalari_change", sozlama.pk)
