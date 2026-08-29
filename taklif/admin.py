from django.contrib import admin
from django.shortcuts import redirect

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


class RSVPInline(admin.TabularInline):
    model = RSVP
    extra = 0
    readonly_fields = ("yaratilgan",)
    fields = ("ism", "keladi", "mehmonlar_soni", "izoh", "mehmon", "yaratilgan")


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
    list_display = ("nomi", "kod", "narx", "ommaviy")
    list_filter = ("ommaviy",)
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
    list_display = (
        "__str__",
        "marosim_turi",
        "sana",
        "shablon",
        "faol",
        "tolangan",
        "yoqdi_bosildi",
        "korishlar",
        "keladiganlar_soni",
        "statistika_link",
    )
    list_filter = ("faol", "tolangan", "marosim_turi", "yoqdi_bosildi", "shablon")
    search_fields = ("ism_1", "ism_2", "slug")
    prepopulated_fields = {"slug": ("ism_1", "ism_2")}
    readonly_fields = (
        "statistika_token", "korishlar", "yaratilgan", "statistika_link", "yoqdi_bosildi",
    )
    inlines = [MehmonInline, TaklifnomaRasmInline, RSVPInline]
    fieldsets = (
        ("Asosiy ma'lumot", {
            "fields": ("marosim_turi", "ism_1", "ism_2", "slug", "shablon", "sana")
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
                "statistika_token", "statistika_link", "yaratilgan",
            )
        }),
    )

    @admin.display(description="Statistika linki")
    def statistika_link(self, obj):
        if obj.pk:
            return obj.get_statistika_url()
        return "-"


@admin.register(Mehmon)
class MehmonAdmin(admin.ModelAdmin):
    list_display = ("ism", "taklifnoma", "slug", "korilgan", "korilgan_vaqt")
    list_filter = ("korilgan",)
    search_fields = ("ism", "taklifnoma__slug", "taklifnoma__ism_1", "taklifnoma__ism_2")
    readonly_fields = ("korilgan", "korilgan_vaqt", "yaratilgan")


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ("ism", "taklifnoma", "mehmon", "keladi", "mehmonlar_soni", "yaratilgan")
    list_filter = ("keladi",)
    search_fields = ("ism", "taklifnoma__slug", "taklifnoma__ism_1", "taklifnoma__ism_2")


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
