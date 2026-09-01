from django.contrib import admin
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import (
    RSVP,
    Mehmon,
    MusiqaVariant,
    NamunaRasm,
    SaytSozlamalari,
    Shablon,
    Taklifnoma,
    TaklifnomaRasm,
)

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


@admin.register(Shablon)
class ShablonAdmin(admin.ModelAdmin):
    # "narx", "turkum", "millat", "marosim_turi" — list_editable: ro'yxatdagi
    # har bir shablonni alohida sahifaga kirmasdan, to'g'ridan-to'g'ri shu
    # yerda belgilash mumkin (o'zgartirib, pastdagi "Saqlash" tugmasini
    # bosish kifoya) — 19 ta mavjud shablonni tez kategoriyalash va
    # kelajakda yangi shablon qo'shishda qulay bo'lishi uchun.
    list_display = ("nomi", "kod", "turkum", "millat", "marosim_turi", "narx", "ommaviy")
    list_editable = ("turkum", "millat", "marosim_turi", "narx")
    list_filter = ("turkum", "millat", "marosim_turi", "ommaviy")
    search_fields = ("nomi", "kod")
    prepopulated_fields = {"kod": ("nomi",)}


@admin.register(MusiqaVariant)
class MusiqaVariantAdmin(admin.ModelAdmin):
    list_display = ("nomi", "til", "faol")
    list_filter = ("til", "faol")
    search_fields = ("nomi",)


@admin.register(NamunaRasm)
class NamunaRasmAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tartib", "faol")
    list_filter = ("faol",)
    search_fields = ("nomi",)


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
                "musiqa_variant", "musiqa", "matn", "sovga_karta", "telegram_link",
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
