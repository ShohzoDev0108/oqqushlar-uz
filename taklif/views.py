from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_POST

from .forms import TaklifnomaYaratishForm
from .models import (
    IKKI_ISMLI_MAROSIM_TURLARI,
    RSVP,
    Mehmon,
    MusiqaVariant,
    Shablon,
    Taklifnoma,
    TaklifnomaRasm,
)

DEFAULT_SHABLON_KOD = "sodda"

# Fotolavha uchun mijoz yuklashi mumkin bo'lgan eng ko'p rasmlar soni.
# Frontendda ham JS orqali tekshiriladi, lekin asosiy himoya shu yerda —
# JS o'chirilgan yoki chetlab o'tilgan taqdirda ham server ortiqchasini kesib tashlaydi.
MAKSIMAL_RASMLAR_SONI = 4

# Mijoz o'zi yaratgan taklifnomalar ro'yxati sessiyada shu kalit ostida saqlanadi
# (login talab qilinmaydi — "Mening taklifnomalarim" bo'limi shu orqali ishlaydi).
SESSIYA_KALITI = "mening_taklifnomalarim_sluglari"


def _sessiyaga_qoshish(request, slug):
    ro_yxat = request.session.get(SESSIYA_KALITI, [])
    if slug in ro_yxat:
        ro_yxat.remove(slug)
    ro_yxat.insert(0, slug)
    request.session[SESSIYA_KALITI] = ro_yxat[:30]
    request.session.modified = True


def _sayt_musiqasi():
    """Joriy interfeys tiliga mos sayt fon musiqasini tanlaydi.

    Mehmon sahifa tilini almashtirsa, keyingi sahifa yuklanishida shu til
    uchun yuklangan musiqa yangraydi. O'sha tilda musiqa bo'lmasa —
    o'zbekchasiga, u ham bo'lmasa istalgan faol variantga tushamiz.
    """
    til = (get_language() or "uz").split("-")[0]
    faollar = MusiqaVariant.objects.filter(faol=True)
    return (
        faollar.filter(til=til).first()
        or faollar.filter(til="uz").first()
        or faollar.first()
    )


def bosh_sahifa(request):
    """Platformaning asosiy landing sahifasi — wedding vibe, shablonlar galereyasi,
    faollashtirilgan taklifnomalar va taklifnoma yaratishga chorlovchi CTA."""
    taklifnomalar = Taklifnoma.objects.filter(faol=True, tolangan=True)[:8]
    shablonlar = Shablon.objects.filter(ommaviy=True)
    return render(
        request,
        "taklif/bosh_sahifa.html",
        {
            "taklifnomalar": taklifnomalar,
            "shablonlar": shablonlar,
            "sayt_musiqa": _sayt_musiqasi(),
        },
    )


def shablon_tanlash(request):
    """Mijoz o'zi taklifnoma yaratishni shu yerdan — shablon tanlashdan boshlaydi."""
    shablonlar = Shablon.objects.filter(ommaviy=True)
    return render(
        request,
        "taklif/shablon_tanlash.html",
        {"shablonlar": shablonlar, "sayt_musiqa": _sayt_musiqasi()},
    )


def yaratish(request, shablon_kod):
    """Mijoz tanlagan shablon bo'yicha o'z taklifnomasini to'ldiradi (self-service)."""
    shablon = get_object_or_404(Shablon, kod=shablon_kod, ommaviy=True)

    if request.method == "POST":
        form = TaklifnomaYaratishForm(request.POST, request.FILES)
        if form.is_valid():
            taklifnoma = form.save(commit=False)
            taklifnoma.shablon = shablon
            # Self-service oqimi: mijoz o'zi yaratganda hali to'lov qilinmagan bo'ladi.
            # Link mijozning o'zi uchun darhol ishlaydi ("lokal"), lekin admin
            # to'lovni tasdiqlab tolangan=True qilmaguncha ommaviy joylarga
            # (bosh sahifa ro'yxati) chiqmaydi.
            taklifnoma.tolangan = False
            taklifnoma.faol = True
            taklifnoma.save()

            for rasm in request.FILES.getlist("rasmlar")[:MAKSIMAL_RASMLAR_SONI]:
                TaklifnomaRasm.objects.create(taklifnoma=taklifnoma, rasm=rasm)

            _sessiyaga_qoshish(request, taklifnoma.slug)

            return redirect("taklif:yaratildi", slug=taklifnoma.slug)
    else:
        form = TaklifnomaYaratishForm()

    return render(
        request,
        "taklif/yaratish.html",
        {
            "form": form,
            "shablon": shablon,
            "ikki_ismli_turlar": list(IKKI_ISMLI_MAROSIM_TURLARI),
            "maksimal_rasmlar_soni": MAKSIMAL_RASMLAR_SONI,
            "sayt_musiqa": _sayt_musiqasi(),
        },
    )


def yaratildi(request, slug):
    """Forma yuborilgach ko'rsatiladigan tasdiq sahifasi — to'lov bo'yicha yo'riqnoma."""
    taklifnoma = get_object_or_404(Taklifnoma, slug=slug)
    context = {
        "taklifnoma": taklifnoma,
        "admin_telegram": settings.SAYT_ADMIN_TELEGRAM,
        "sayt_musiqa": _sayt_musiqasi(),
    }
    return render(request, "taklif/yaratildi.html", context)


def _taklifnoma_sahifasi(request, taklifnoma, mehmon=None):
    """korish va mehmon_korish uchun umumiy render mantig'i.

    mehmon berilsa (shaxsiy link orqali kirilgan bo'lsa), sahifa uni ismi
    bilan kutib oladi, RSVP formasi oldindan to'ldiriladi va "ko'rdi" deb
    belgilanadi.
    """
    if not taklifnoma.faol:
        return render(
            request, "taklif/muddati_tugagan.html", {"taklifnoma": taklifnoma}
        )

    # Ko'rishlar sonini race-condition'siz oshirish
    Taklifnoma.objects.filter(pk=taklifnoma.pk).update(korishlar=F("korishlar") + 1)

    if mehmon and not mehmon.korilgan:
        Mehmon.objects.filter(pk=mehmon.pk).update(
            korilgan=True, korilgan_vaqt=timezone.now()
        )

    # Mehmonlar jadvali — faqat "keladi" deb javob berganlar ochiq ko'rinadi,
    # kelmasligini bildirganlar ochiq bo'lmasligi kerak (statistika sahifasi maxfiy)
    mehmonlar = taklifnoma.javoblar.filter(keladi=True).order_by("-yaratilgan")

    context = {
        "taklifnoma": taklifnoma,
        "mehmon": mehmon,
        "mehmonlar": mehmonlar,
        "mehmonlar_jami": taklifnoma.keladiganlar_soni,
        "rasmlar": taklifnoma.rasmlar.all(),
        "admin_telegram": settings.SAYT_ADMIN_TELEGRAM,
    }
    return render(request, _shablon_fayli(taklifnoma.shablon.kod), context)


def korish(request, slug):
    """Mehmonlar (yoki mijozning o'zi) uchun ochiq — umumiy — taklifnoma sahifasi."""
    taklifnoma = get_object_or_404(
        Taklifnoma.objects.select_related("shablon"), slug=slug
    )
    return _taklifnoma_sahifasi(request, taklifnoma)


def mehmon_korish(request, slug, mehmon_slug):
    """Bitta mehmon uchun shaxsiylashtirilgan link — ismi bilan kutib oladi."""
    taklifnoma = get_object_or_404(
        Taklifnoma.objects.select_related("shablon"), slug=slug
    )
    mehmon = get_object_or_404(Mehmon, taklifnoma=taklifnoma, slug=mehmon_slug)
    return _taklifnoma_sahifasi(request, taklifnoma, mehmon=mehmon)


def _shablon_fayli(shablon_kod):
    """Shablon kodiga mos HTML faylni tanlaydi; topilmasa standart shablonga tushadi.

    Bu orqali kelajakda yangi shablon qo'shish uchun faqat
    taklif/templates/taklif/shablonlar/<kod>.html faylini qo'shish kifoya.
    """
    nomzod = f"taklif/shablonlar/{shablon_kod}.html"
    try:
        get_template(nomzod)
        return nomzod
    except TemplateDoesNotExist:
        return f"taklif/shablonlar/{DEFAULT_SHABLON_KOD}.html"


@require_POST
def rsvp_submit(request, slug):
    """Mehmon RSVP formasini yuborishi."""
    taklifnoma = get_object_or_404(Taklifnoma, slug=slug, faol=True)

    ism = request.POST.get("ism", "").strip()
    keladi = request.POST.get("keladi") == "ha"
    izoh = request.POST.get("izoh", "").strip()
    mehmon_slug = request.POST.get("mehmon_slug", "").strip()
    try:
        mehmonlar_soni = int(request.POST.get("mehmonlar_soni", 1))
    except ValueError:
        mehmonlar_soni = 1

    mehmon = None
    if mehmon_slug:
        mehmon = Mehmon.objects.filter(taklifnoma=taklifnoma, slug=mehmon_slug).first()

    if ism:
        RSVP.objects.create(
            taklifnoma=taklifnoma,
            mehmon=mehmon,
            ism=ism,
            keladi=keladi,
            mehmonlar_soni=max(1, min(5, mehmonlar_soni)),
            izoh=izoh,
        )
        messages.success(request, _("Javobingiz uchun rahmat!"))
    else:
        messages.error(request, _("Iltimos, ismingizni kiriting."))

    if mehmon:
        return redirect("taklif:mehmon_korish", slug=slug, mehmon_slug=mehmon.slug)
    return redirect("taklif:korish", slug=slug)


def mening_taklifnomalarim(request):
    """Mijoz sessiya davomida o'zi yaratgan taklifnomalarni solishtirish uchun ko'radi."""
    sluglar = request.session.get(SESSIYA_KALITI, [])
    taklifnomalar_map = {
        t.slug: t
        for t in Taklifnoma.objects.select_related("shablon").filter(slug__in=sluglar)
    }
    # Sessiyada saqlangan tartibda (eng yangisi birinchi) ko'rsatamiz
    taklifnomalar = [taklifnomalar_map[s] for s in sluglar if s in taklifnomalar_map]
    return render(
        request,
        "taklif/mening_taklifnomalarim.html",
        {"taklifnomalar": taklifnomalar, "sayt_musiqa": _sayt_musiqasi()},
    )


def yoqdi(request, slug):
    """Mijoz 'Yoqdi' tugmasini bosganda: belgilab qo'yamiz va adminga Telegram orqali
    xabar yozish uchun tayyor havolaga yo'naltiramiz."""
    taklifnoma = get_object_or_404(Taklifnoma, slug=slug)
    if not taklifnoma.yoqdi_bosildi:
        Taklifnoma.objects.filter(pk=taklifnoma.pk).update(yoqdi_bosildi=True)

    xabar = (
        f"Assalomu alaykum! Menga \"{taklifnoma.sarlavha}\" taklifnomasi "
        f"({request.build_absolute_uri(taklifnoma.get_absolute_url())}) yoqdi, "
        "to'lov qilib faollashtirmoqchiman."
    )
    admin_username = settings.SAYT_ADMIN_TELEGRAM.lstrip("@")
    telegram_url = f"https://t.me/{admin_username}?text={quote(xabar)}"
    return redirect(telegram_url)


def statistika(request, token):
    """Faqat mijoz ko'radigan maxfiy statistika sahifasi (token orqali)."""
    taklifnoma = get_object_or_404(Taklifnoma, statistika_token=token)
    javoblar = taklifnoma.javoblar.all().order_by("-yaratilgan")
    mehmonlar = taklifnoma.mehmonlar.all().order_by("ism")

    context = {
        "taklifnoma": taklifnoma,
        "javoblar": javoblar,
        "mehmonlar": mehmonlar,
        "keladiganlar_soni": taklifnoma.keladiganlar_soni,
        "kelmaydiganlar_soni": taklifnoma.kelmaydiganlar_soni,
    }
    return render(request, "taklif/statistika.html", context)
