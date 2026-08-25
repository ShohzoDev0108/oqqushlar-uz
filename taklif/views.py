import secrets
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_POST

from .forms import REZERV_SLUGLAR, TaklifnomaYaratishForm
from .models import (
    IKKI_ISMLI_MAROSIM_TURLARI,
    RSVP,
    Mehmon,
    MusiqaVariant,
    Shablon,
    Taklifnoma,
    TaklifnomaRasm,
)

# Havola (slug) mijozdan hech qachon so'ralmaydi — ko'pchilik mijoz "manzil"
# yoki "link" degan texnik tushunchani tushunmaydi. Agar ism_1+ism_2 asosidagi
# toza havola band bo'lib chiqsa (masalan boshqa mijozda tasodifan bir xil
# ism bo'lsa), buni mijozga bildirmasdan — orqa fondan, xunuk "-2"/"-3" kabi
# raqam qo'shmasdan, mazmunli so'z bilan ajratamiz.
DISAMBIGUATSIYA_SOZLARI = [
    "baxtli", "muhabbat", "quvonch", "umrbod", "sadoqat",
    "porloq", "bahor", "sevimli", "shodlik", "najot",
]


def _asosiy_slug(ism_1, ism_2):
    """Mijoz ismlaridan toza havola (slug) yasaydi — mijoz buni ko'rmaydi/tahrirlamaydi."""
    manba = f"{ism_1}-{ism_2}" if ism_2 else ism_1
    return slugify(manba) or "taklifnoma"


def _band_emasligini_tekshir(slug, chetlanganlar):
    return (
        slug not in chetlanganlar
        and slug not in REZERV_SLUGLAR
        and not Taklifnoma.objects.filter(slug=slug).exists()
    )


def _bosh_slug_top(asosiy, sana=None, marosim_turi="", toyxona="", chetlanganlar=()):
    """Asosiy nom band bo'lib chiqsa, mijozga bildirmasdan — orqa fondan
    mazmunli (sana, to'yxona, marosim turi yoki chiroyli so'z bilan)
    band bo'lmagan havola topadi. Hech qachon xunuk "-2", "-3" qo'shilmaydi."""
    chetlanganlar = set(chetlanganlar)

    if _band_emasligini_tekshir(asosiy, chetlanganlar):
        return asosiy

    nomzodlar = []
    if sana:
        nomzodlar.append(f"{asosiy}-{sana.day:02d}-{sana.month:02d}")
    if toyxona:
        toyxona_slug = slugify(toyxona)
        if toyxona_slug:
            nomzodlar.append(f"{asosiy}-{toyxona_slug}")
    if marosim_turi:
        nomzodlar.append(f"{asosiy}-{marosim_turi.replace('_', '-')}")
    for soz in DISAMBIGUATSIYA_SOZLARI:
        nomzodlar.append(f"{asosiy}-{soz}")

    for nomzod in nomzodlar:
        if _band_emasligini_tekshir(nomzod, chetlanganlar):
            return nomzod

    # Amalda deyarli imkonsiz holat uchun oxirgi chora
    return f"{asosiy}-{secrets.token_hex(3)}"

# "sodda" va boshqa eng birinchi/eng oddiy 8 ta shablon olib tashlangani
# uchun (mijoz taklifiga ko'ra) standart holat sifatida to'liq funksiyali
# shablonlardan biriga tushamiz.
DEFAULT_SHABLON_KOD = "suzani"

# Fotolavha uchun mijoz yuklashi mumkin bo'lgan eng ko'p rasmlar soni.
# Ataylab 2 tagacha cheklangan — sahifada katta, ekranni to'ldiradigan
# formatda (1 ta bo'lsa — to'liq kenglikda, 2 ta bo'lsa — yonma-yon)
# ko'rsatiladi, shuning uchun ko'proq rasm bu ko'rinishga sig'may qoladi.
# Frontendda ham JS orqali tekshiriladi, lekin asosiy himoya shu yerda —
# JS o'chirilgan yoki chetlab o'tilgan taqdirda ham server ortiqchasini kesib tashlaydi.
MAKSIMAL_RASMLAR_SONI = 2

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
    """Mijoz tanlagan shablon bo'yicha o'z taklifnomasini to'ldiradi (self-service).

    Havola (slug) mijozdan hech qachon so'ralmaydi — ism_1/ism_2'dan avtomatik
    yasaladi. Agar mijoz shu brauzerda avval xuddi shu ismlar bilan taklifnoma
    yaratgan bo'lsa — "eski_taklifnoma" shu yerga qo'yiladi, shablon esa
    mijozdan oddiy tilda ("link"/"manzil" so'zisiz) nima qilishni so'raydi.
    """
    shablon = get_object_or_404(Shablon, kod=shablon_kod, ommaviy=True)
    eski_taklifnoma = None

    if request.method == "POST":
        form = TaklifnomaYaratishForm(request.POST, request.FILES)
        if form.is_valid():
            ism_1 = form.cleaned_data["ism_1"]
            ism_2 = form.cleaned_data.get("ism_2") or ""
            sana = form.cleaned_data.get("sana")
            toyxona = form.cleaned_data.get("toyxona") or ""
            marosim_turi = form.cleaned_data.get("marosim_turi") or ""

            asosiy = _asosiy_slug(ism_1, ism_2)
            mavjud = Taklifnoma.objects.filter(slug=asosiy).first()
            slug = asosiy
            yaratish_kerak = True

            if mavjud is not None:
                oldingi_sluglar = request.session.get(SESSIYA_KALITI, [])
                ozimniki = asosiy in oldingi_sluglar
                harakat = request.POST.get("eski_taklifnoma_harakati")

                if ozimniki and harakat == "yangilash":
                    # Mijoz tasdiqladi: eski (yoqmagan) taklifnoma o'chirilib,
                    # xuddi shu toza havolaga yangisi yaratiladi.
                    mavjud.delete()
                elif ozimniki and harakat == "alohida":
                    # Mijoz ikkalasini ham saqlab qolmoqchi — mijozga hech
                    # narsa bildirmasdan, orqa fondan mazmunli havola topamiz.
                    slug = _bosh_slug_top(asosiy, sana, marosim_turi, toyxona)
                elif ozimniki:
                    # Mijozning o'zi avval shu ismlar bilan yaratgan — xato
                    # ko'rsatmaymiz, oddiy tilda so'raymiz: yangilaymizmi yoki
                    # alohida saqlaymizmi?
                    eski_taklifnoma = mavjud
                    yaratish_kerak = False
                else:
                    # Bu boshqa mijozda tasodifan bir xil ism chiqib qoldi —
                    # mijozga bu haqda umuman bildirmaymiz, shunchaki orqa
                    # fondan mazmunli (raqamsiz) havola topib beramiz.
                    slug = _bosh_slug_top(asosiy, sana, marosim_turi, toyxona)

            if yaratish_kerak:
                taklifnoma = form.save(commit=False)
                taklifnoma.slug = slug
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
            "eski_taklifnoma": eski_taklifnoma,
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
