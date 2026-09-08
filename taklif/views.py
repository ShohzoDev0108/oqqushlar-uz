import logging
import os
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.core.files.base import ContentFile
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import get_language, gettext as _
from django.views.decorators.http import require_POST

from .forms import (
    MAROSIM_MAYDON_MATNLARI,
    OY_NOMLARI,
    REZERV_SLUGLAR,
    STANDART_MAROSIM_TURI,
    TaklifnomaYaratishForm,
)
from .models import (
    CHIQINDI_SAQLASH_KUNLARI,
    DASTUR_MAKS_BAND,
    IKKI_ISMLI_MAROSIM_TURLARI,
    MAROSIM_DASTUR_NAMUNALARI,
    MAROSIM_TURLARI,
    MILLATLAR,
    RASM_MAKS_HAJM_MB,
    UCHINCHI_ISM_MAROSIM_TURLARI,
    RSVP,
    Mehmon,
    MusiqaVariant,
    NamunaRasm,
    SaytSozlamalari,
    Shablon,
    Taklifnoma,
    TaklifnomaRasm,
)
from .namuna import (
    marosim_tanlash,
    namuna_taklifnomasi,
    sessiyadagi_tilak,
    sessiyaga_tilak_yoz,
    tayyor_tilaklar,
)
from .ulashish import kartochka, reklama_kartochkasi

_logger = logging.getLogger("django.request")

# Havola (slug) mijozdan hech qachon so'ralmaydi — ko'pchilik mijoz "manzil"
# yoki "link" degan texnik tushunchani tushunmaydi. Agar ism_1+ism_2 asosidagi
# toza havola band bo'lib chiqsa (masalan boshqa mijozda tasodifan bir xil
# ism bo'lsa), buni mijozga bildirmasdan — orqa fondan, xunuk "-2"/"-3" kabi
# raqam qo'shmasdan, mazmunli so'z bilan ajratamiz.
DISAMBIGUATSIYA_SOZLARI = [
    "baxtli", "muhabbat", "quvonch", "umrbod", "sadoqat",
    "porloq", "bahor", "sevimli", "shodlik", "najot",
]

# Taklifnoma.slug maydonining haqiqiy sig'imi (SlugField standart bo'yicha
# 50 belgi). Buni modeldan o'zi o'qiymiz — kelajakda model o'zgarsa ham bu
# yerda qo'lda yangilash kerak bo'lmaydi.
#
# DIQQAT: ism_1/ism_2 har biri 100 belgigacha bo'lishi mumkin (modelga
# qarang) — ya'ni ular birlashtirilgan slug ayni maydon sig'imidan OSON
# OSHIB KETISHI mumkin edi. Bu SQLite'da sezilmas edi (u VARCHAR(n)
# uzunligini qat'iy tekshirmaydi), lekin PostgreSQL'ga o'tganda "value too
# long for type character varying(50)" xatosi bilan mijozning taklifnoma
# yaratish jarayoni to'xtab qolardi — shuning uchun quyida har bir
# bo'lakni maydon sig'imiga qarab qat'iy cheklaymiz.
_SLUG_MAX_UZUNLIK = Taklifnoma._meta.get_field("slug").max_length
_SLUG_ASOSIY_MAX = _SLUG_MAX_UZUNLIK - 20  # qo'shimcha (sana/so'z) uchun joy


def _asosiy_slug(ism_1, ism_2, ism_3=""):
    """Mijoz ismlaridan toza havola (slug) yasaydi — mijoz buni ko'rmaydi/tahrirlamaydi."""
    ismlar = [ism for ism in (ism_1, ism_2, ism_3) if ism]
    manba = "-".join(ismlar)
    slug = slugify(manba) or "taklifnoma"
    return slug[:_SLUG_ASOSIY_MAX].rstrip("-") or "taklifnoma"


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

    # asosiy — yuqorida _asosiy_slug() orqali allaqachon qisqartirilgan;
    # shunga qaramay, har bir qo'shimcha bo'lak ham o'zi uzun bo'lishi
    # mumkinligi uchun (masalan to'yxona nomi 200 belgigacha) alohida
    # cheklanadi va yakuniy natija yana bir bor xavfsizlik uchun kesiladi.
    nomzodlar = []
    if sana:
        nomzodlar.append(f"{asosiy}-{sana.day:02d}-{sana.month:02d}")
    if toyxona:
        toyxona_slug = slugify(toyxona)[:20]
        if toyxona_slug:
            nomzodlar.append(f"{asosiy}-{toyxona_slug}")
    if marosim_turi:
        nomzodlar.append(f"{asosiy}-{marosim_turi.replace('_', '-')[:20]}")
    for soz in DISAMBIGUATSIYA_SOZLARI:
        nomzodlar.append(f"{asosiy}-{soz}")

    for nomzod in nomzodlar:
        nomzod = nomzod[:_SLUG_MAX_UZUNLIK]
        if _band_emasligini_tekshir(nomzod, chetlanganlar):
            return nomzod

    # Amalda deyarli imkonsiz holat uchun oxirgi chora
    return f"{asosiy}-{secrets.token_hex(3)}"[:_SLUG_MAX_UZUNLIK]

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

# Bitta brauzer/sessiya bitta taklifnomani bir necha marta qayta ochsa (sahifani
# yangilasa), "ko'rishlar" soni faqat BIRINCHI safar oshsin deb — shu kalit
# ostida allaqachon ko'rilgan taklifnomalar sluglari saqlanadi.
KORISH_SESSIYA_KALITI = "korilgan_taklifnoma_sluglari"


def _rasmlar_xatosini_tekshir(request):
    """Mijoz o'zi yuklagan (tayyor namuna emas) fotolarning hajmini tekshiradi.

    TaklifnomaRasm ModelForm orqali emas, to'g'ridan-to'g'ri yaratilgani
    uchun (pastdagi _taklifnoma_rasmlarini_saqlash) modeldagi
    FaylHajmiValidator bu yo'lda avtomatik ishlamaydi — shu uchun alohida
    tekshiramiz. Xato topilsa, matnni qaytaradi; hammasi joyida bo'lsa None.
    """
    maks_bayt = RASM_MAKS_HAJM_MB * 1024 * 1024
    for fayl in request.FILES.getlist("rasmlar"):
        if fayl.size > maks_bayt:
            return _(
                "\"%(nomi)s\" fayli juda katta (%(hajm).1f MB). Rasm hajmi "
                "%(maks)s MB dan oshmasligi kerak."
            ) % {
                "nomi": fayl.name,
                "hajm": fayl.size / (1024 * 1024),
                "maks": RASM_MAKS_HAJM_MB,
            }
    return None


def _taklifnoma_rasmlarini_saqlash(taklifnoma, request):
    """Mijoz tanlagan tayyor namuna rasmlar va/yoki o'zi yuklagan fayllarni
    birlashtirib, TaklifnomaRasm sifatida saqlaydi (musiqadagi "tayyor
    variant yoki o'zi yuklash" bilan bir xil mantiq).

    Namuna rasm tanlansa, uning fayli mijozning shaxsiy nusxasiga
    ko'chiriladi — kelajakda namunalar ro'yxati o'zgarsa ham, mijozning
    taklifnomasi buzilmaydi. Jami rasmlar soni har doim
    MAKSIMAL_RASMLAR_SONI bilan cheklanadi (namuna + yuklangan birgalikda).
    """
    tartib = 0

    namuna_idlari = request.POST.getlist("namuna_rasm_ids")
    if namuna_idlari:
        tanlangan_namunalar = NamunaRasm.objects.filter(
            id__in=namuna_idlari, faol=True
        )
        # POST tartibiga mos ketishi uchun
        tartibli = sorted(
            tanlangan_namunalar, key=lambda n: namuna_idlari.index(str(n.id))
        )
        for namuna in tartibli:
            if tartib >= MAKSIMAL_RASMLAR_SONI:
                break
            try:
                namuna.rasm.open("rb")
                nusxa = ContentFile(
                    namuna.rasm.read(), name=os.path.basename(namuna.rasm.name)
                )
                namuna.rasm.close()
            except (FileNotFoundError, OSError):
                # Taftish topilmasi: bazadagi NamunaRasm yozuvi mavjud, lekin
                # unga tegishli fayl xotirada (R2/S3) haqiqatda yo'q edi —
                # masalan admin faylni tashqaridan o'chirib yuborgan yoki
                # yuklash muvaffaqiyatsiz tugagan holatda. Bu xato oldin
                # ushlanmagani uchun mijozning BUTUN taklifnoma yaratish
                # so'rovi 500-xato bilan qulab tushardi (mijoz o'z rasmlarini
                # ham, matnini ham yo'qotardi) — shu bitta buzuq namuna sabab.
                # Endi shu bitta namunani jimgina o'tkazib yuboramiz (mijoz
                # so'rovi davom etadi), lekin xatoni "django.request" logeriga
                # yozamiz — bu Telegram xabarnomasini ishga tushiradi, shunda
                # admin buzuq namunani tezda tuzatishi (qayta yuklashi yoki
                # o'chirishi) mumkin.
                _logger.error(
                    "Namuna rasm topilmadi (id=%s, fayl=%s) — o'tkazib yuborildi",
                    namuna.id,
                    getattr(namuna.rasm, "name", None),
                    exc_info=True,
                )
                continue
            TaklifnomaRasm.objects.create(
                taklifnoma=taklifnoma, rasm=nusxa, tartib=tartib
            )
            tartib += 1

    for rasm in request.FILES.getlist("rasmlar"):
        if tartib >= MAKSIMAL_RASMLAR_SONI:
            break
        TaklifnomaRasm.objects.create(taklifnoma=taklifnoma, rasm=rasm, tartib=tartib)
        tartib += 1


def _sessiyaga_qoshish(request, slug):
    ro_yxat = request.session.get(SESSIYA_KALITI, [])
    if slug in ro_yxat:
        ro_yxat.remove(slug)
    ro_yxat.insert(0, slug)
    request.session[SESSIYA_KALITI] = ro_yxat[:30]
    request.session.modified = True


def _sayt_musiqasi():
    """Joriy interfeys tiliga mos musiqa variantini tanlaydi.

    O'sha tilda musiqa bo'lmasa — o'zbekchasiga, u ham bo'lmasa istalgan
    faol variantga tushamiz.

    TAFTISH: bu funksiya ilgari HAR BIR sayt sahifasiga fon musiqasi
    berardi. Sayt musiqasi olib tashlangach (sabab: _sayt_musiqa.html
    izohi) u faqat BITTA joyda qoldi — namuna taklifnomasi uchun. Namuna
    haqiqiy taklifnomaga to'liq o'xshashi kerak, taklifnomada esa musiqa
    bor.
    """
    til = (get_language() or "uz").split("-")[0]
    faollar = MusiqaVariant.objects.filter(faol=True)
    return (
        faollar.filter(til=til).first()
        or faollar.filter(til="uz").first()
        or faollar.first()
    )


# Bosh sahifadagi telefon maketi ichida aylanadigan slaydlar.
#
# NEGA. Maketda bitta, o'zgarmas nikoh to'yi ekrani turardi — ya'ni
# tashrifchi saytga kirib "bu to'y taklifnomasi sayti ekan" degan
# xulosaga kelardi. Holbuki dizaynlarning yarmi boshqa marosimlar
# uchun: beshik to'yi, nahor oshi, xatna to'yi, yubiley... Ular haqida
# bilish uchun pastga tushib, katalogni ochib, marosim filtrini
# tanlash kerak edi. Endi telefon ekranining o'zi ularni birma-bir
# ko'rsatadi.
#
# "kod" — shu marosim uchun chizilgan tasvir papkasi
# (taklif/static/taklif/<kod>/<kod>-hero.webp). Nikoh to'yida bunday
# tasvir yo'q, uning o'rniga saytning o'z belgisi chiziladi — shu
# sabab "kod" bo'sh qoldirilgan.
BOSH_SLAYDLAR = [
    # "kod" — shu marosim uchun chizilgan tasvir papkasi
    # (taklif/static/taklif/<kod>/<kod>-hero.webp). Nikoh to'yida bunday
    # tasvir yo'q, uning o'rniga saytning o'z belgisi chiziladi.
    # "namuna" — "Ochib ko'rish" tugmasi qaysi dizayn namunasini ochishi.
    {"marosim": "toy", "kod": "", "namuna": "sadaf", "ism_1": "Aziz", "ism_2": "Nilufar"},
    {"marosim": "fotiha_toy", "kod": "fotiha", "namuna": "fotiha", "ism_1": "Sanjar", "ism_2": "Nilufar"},
    {"marosim": "qizlar_bazmi", "kod": "qizuzatish", "namuna": "qizuzatish", "ism_1": "Zilola", "ism_2": ""},
    {"marosim": "sunnat_toy", "kod": "xatna", "namuna": "xatna", "ism_1": "Amirbek", "ism_2": "Sardorbek"},
    {"marosim": "beshik_toy", "kod": "beshik", "namuna": "beshik", "ism_1": "Oysha", "ism_2": ""},
    {"marosim": "nahor_oshi", "kod": "nahoroshi", "namuna": "nahoroshi", "ism_1": "Rustam", "ism_2": ""},
    {"marosim": "yubiley", "kod": "yubiley", "namuna": "yubiley", "ism_1": "Gulchehra", "ism_2": ""},
    {"marosim": "tugilgan_kun", "kod": "tugilgankun", "namuna": "tugilgankun", "ism_1": "Diyorbek", "ism_2": ""},
]


def _bosh_slaydlar():
    """Telefon maketidagi slaydlarni marosim nomi va sanasi bilan to'ldiradi."""
    nomlar = dict(MAROSIM_TURLARI)
    hozir = timezone.localtime(timezone.now())
    natija = []
    for i, s in enumerate(BOSH_SLAYDLAR):
        # Har bir slaydga o'z sanasi — bitta sana takrorlansa, maket
        # "yasama" ko'rinadi.
        sana = hozir + timedelta(days=38 + i * 11)
        natija.append(dict(s, nomi=nomlar.get(s["marosim"], ""), sana=sana))
    return natija


def bosh_sahifa(request):
    """Platformaning asosiy landing sahifasi — wedding vibe, shablonlar galereyasi,
    faollashtirilgan taklifnomalar va taklifnoma yaratishga chorlovchi CTA."""
    # Faqat mijozning o'zi aniq rozilik bildirgan (ommaviy_korsatishga_rozi=True)
    # taklifnomalar ko'rsatiladi — ism va marosim sanasi kabi shaxsiy
    # ma'lumotlarni mijoz roziligisiz ochiq ko'rsatmaslik uchun (taftish topilmasi).
    taklifnomalar = Taklifnoma.objects.filter(
        faol=True, tolangan=True, ommaviy_korsatishga_rozi=True
    )[:8]
    shablonlar = Shablon.objects.filter(ommaviy=True)
    return render(
        request,
        "taklif/bosh_sahifa.html",
        {
            "taklifnomalar": taklifnomalar,
            "shablonlar": shablonlar,
            "admin_telegram": _admin_telegram(),
            "bosh_slaydlar": _bosh_slaydlar(),
        },
    )


def shablon_tanlash(request):
    """Mijoz o'zi taklifnoma yaratishni shu yerdan — shablon tanlashdan boshlaydi.

    Uch bosqichli filtr: Marosim turi (majburiy, birinchi qadam) + Turkum
    (Zamonaviy/Milliy/Islomiy) + Millat (faqat Milliy ichida).

    Marosim turlari BUTUN ro'yxat bilan, yashirmasdan ko'rsatiladi —
    "Boshqa" ham shular qatorida. "Boshqa" — mijoz tadbir nomini o'zi
    yozadigan tur (masalan "11-sinf o'quvchilari"); u faqat shu yerdan
    tanlanadi, chunki taklifnoma to'ldirish sahifasida marosim turi
    endi qayta so'ralmaydi (yaratish() ga qarang). Shu sababli uni
    ro'yxatdan chiqarib tashlab bo'lmaydi — aks holda mijoz o'z nomli
    tadbiriga taklifnoma yasay olmay qolardi.

    Tanlangan tur mijoz bosgan dizayn havolasiga ?marosim=<kalit> bo'lib
    qo'shiladi (shablon_tanlash.html'dagi JS).
    """
    shablonlar = Shablon.objects.filter(ommaviy=True)
    return render(
        request,
        "taklif/shablon_tanlash.html",
        {
            "shablonlar": shablonlar,
            "marosim_turlari": list(MAROSIM_TURLARI),
            "millatlar": MILLATLAR,
        },
    )


def biz_haqimizda(request):
    """Xizmat haqida qisqacha ma'lumot sahifasi."""
    return render(
        request,
        "taklif/biz_haqimizda.html",
        {
            "admin_telegram": _admin_telegram(),
        },
    )


def savol_javob(request):
    """Savol-javob — o'z sahifasi sifatida.

    Savollar ro'yxatining o'zi _savol_javob_royxati.html qismida: xuddi
    shu ro'yxat bosh sahifada ham ko'rsatiladi, ya'ni javoblar bir joyda
    saqlanadi va ikki nusxaga bo'linib ketmaydi.
    """
    return render(request, "taklif/savol_javob.html")



def narxlar(request):
    """Narxlar sahifasi — nima kiradi, nima alohida kelishiladi, to'lov tartibi.

    "shablonlar" kerak: narx kartasi eng arzon dizayn narxini o'zi
    hisoblaydi (_narx_karta.html), shu sabab admin panelda narx
    o'zgartirilsa bu sahifa ham o'zi yangilanadi.
    """
    return render(
        request,
        "taklif/narxlar.html",
        {
            "shablonlar": Shablon.objects.filter(ommaviy=True),
            "admin_telegram": _admin_telegram(),
        },
    )

def boglanish(request):
    """Bog'lanish — o'z sahifasi sifatida.

    Avval u "Biz haqimizda" sahifasining ichki bo'limi (#boglanish)
    edi, lekin menyudan bosilganda mijoz boshqa sahifaning o'rtasiga
    tushib qolardi — o'z sarlavhasi bo'lgan alohida sahifa aniqroq.
    """
    return render(
        request,
        "taklif/boglanish.html",
        {
            "admin_telegram": _admin_telegram(),
        },
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

    # Mijoz shablon tanlash sahifasida marosim turini allaqachon tanlagan
    # bo'ladi va u bu yerga ?marosim=<kalit> orqali keladi
    # (shablon_tanlash.html'dagi JS havolani shunday yasaydi). Shu holda
    # "Marosim turi" maydoni formada UMUMAN ko'rsatilmaydi — javob
    # ma'lum, mijozdan ikkinchi marta so'rash faqat chalkashtiradi
    # (maydonning o'zi DOM'da qoladi: sahifadagi JS uning qiymatiga
    # qarab boshqa maydonlar yorlig'ini, musiqa va rasm namunalarini
    # moslaydi).
    #
    # Agar qiymat kelmasa yoki noto'g'ri bo'lsa (mijoz to'g'ridan-to'g'ri
    # havola bilan kirgan, xatcho'pdan ochgan va h.k.) — maydon odatdagidek
    # ko'rinadi va so'raladi.
    marosim_kalitlari = {k for k, _ in MAROSIM_TURLARI}
    oldindan_marosim = request.GET.get("marosim") or ""
    if oldindan_marosim not in marosim_kalitlari:
        oldindan_marosim = ""

    if request.method == "POST":
        form = TaklifnomaYaratishForm(request.POST, request.FILES)
        if form.is_valid():
            # TaklifnomaRasm to'g'ridan-to'g'ri (ModelForm orqali emas)
            # yaratiladi (pastda _taklifnoma_rasmlarini_saqlash), shuning
            # uchun modeldagi FaylHajmiValidator bu yerda avtomatik
            # ishlamaydi — shu tekshiruvni forma tasdiqlangandan keyin,
            # lekin hali hech narsa saqlanmasdan oldin, qo'lda bajaramiz
            # (aks holda mijozning taklifnomasi yaratilib, keyin rasm xatosi
            # chiqib, chala/rasmisiz taklifnoma qolib ketishi mumkin edi).
            rasm_xatosi = _rasmlar_xatosini_tekshir(request)
            if rasm_xatosi:
                form.add_error(None, rasm_xatosi)
            else:
                ism_1 = form.cleaned_data["ism_1"]
                ism_2 = form.cleaned_data.get("ism_2") or ""
                ism_3 = form.cleaned_data.get("ism_3") or ""
                sana = form.cleaned_data.get("sana")
                toyxona = form.cleaned_data.get("toyxona") or ""
                marosim_turi = form.cleaned_data.get("marosim_turi") or ""

                asosiy = _asosiy_slug(ism_1, ism_2, ism_3)
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

                    _taklifnoma_rasmlarini_saqlash(taklifnoma, request)

                    _sessiyaga_qoshish(request, taklifnoma.slug)

                    return redirect("taklif:yaratildi", slug=taklifnoma.slug)
    else:
        form = TaklifnomaYaratishForm(
            initial={"marosim_turi": oldindan_marosim} if oldindan_marosim else None
        )

    # MAROSIM_MAYDON_MATNLARI'dagi lazy tarjima obyektlarini shu yerda,
    # so'rov tiliga qarab, oddiy matnga aylantiramiz — json_script faqat
    # JSON-ga to'g'ridan-to'g'ri serializatsiya qilinadigan qiymatlarni
    # qabul qiladi (lazy obyektni emas).
    marosim_maydon_matnlari_json = {
        turi: {kalit: str(qiymat) for kalit, qiymat in matnlar.items()}
        for turi, matnlar in MAROSIM_MAYDON_MATNLARI.items()
    }

    # Kun tartibi namunalari ham xuddi shunday: lazy tarjimalar JSON'ga
    # tushmaydi, shuning uchun so'rov tilida oddiy matnga aylantiriladi.
    dastur_namunalari_json = {
        turi: [
            {kalit: str(qiymat) for kalit, qiymat in band.items()}
            for band in bandlar
        ]
        for turi, bandlar in MAROSIM_DASTUR_NAMUNALARI.items()
    }

    return render(
        request,
        "taklif/yaratish.html",
        {
            "form": form,
            "shablon": shablon,
            "ikki_ismli_turlar": list(IKKI_ISMLI_MAROSIM_TURLARI),
            "uch_ismli_turlar": list(UCHINCHI_ISM_MAROSIM_TURLARI),
            "marosim_maydon_matnlari": marosim_maydon_matnlari_json,
            "dastur_namunalari": dastur_namunalari_json,
            "dastur_maks_band": DASTUR_MAKS_BAND,
            "standart_marosim_turi": STANDART_MAROSIM_TURI,
            "marosim_oldindan": bool(oldindan_marosim),
            "oy_nomlari": [str(oy) for oy in OY_NOMLARI],
            "maksimal_rasmlar_soni": MAKSIMAL_RASMLAR_SONI,
            "namuna_rasmlar": NamunaRasm.objects.filter(faol=True),
            "musiqa_variantlar": MusiqaVariant.objects.filter(faol=True),
            "eski_taklifnoma": eski_taklifnoma,
            "admin_telegram": _admin_telegram(),
        },
    )


def _admin_telegram():
    """Admin panelida sozlangan Telegram username, bo'sh bo'lsa serverdagi
    standart (SAYT_ADMIN_TELEGRAM environment o'zgaruvchisi) qiymat."""
    return SaytSozlamalari.olish().admin_telegram or settings.SAYT_ADMIN_TELEGRAM


def yaratildi(request, slug):
    """Forma yuborilgach ko'rsatiladigan tasdiq sahifasi — to'lov bo'yicha yo'riqnoma."""
    taklifnoma = get_object_or_404(Taklifnoma, slug=slug)
    context = {
        "taklifnoma": taklifnoma,
        "admin_telegram": _admin_telegram(),
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

    if not taklifnoma.tolangan:
        # Hali to'lov admin tomonidan tasdiqlanmagan (tolangan=False):
        # faqat shu taklifnomani YARATGAN kishining o'zi (session orqali —
        # xuddi "Mening taklifnomalarim" ro'yxatidagidek) uni oldindan
        # ko'rib chiqa oladi. Boshqa istalgan kishi (mehmon yoki tasodifiy
        # tashrifchi) hali ko'ra olmaydi — aks holda mijoz hech qachon
        # to'lamasdan ham linkni to'g'ridan-to'g'ri mehmonlarga ulashib
        # yuborishi mumkin bo'lar edi.
        sluglar = request.session.get(SESSIYA_KALITI, [])
        if taklifnoma.slug not in sluglar:
            # DIQQAT: "taklifnoma" bu yerda context'ga qasddan berilmaydi —
            # base.html'ning Open Graph/Twitter meta teglari `taklifnoma`
            # mavjud bo'lsa uning sarlavhasini (mijoz ismini) avtomatik
            # chiqarib yuboradi. Hali ruxsat berilmagan tashrifchiga hatto
            # meta teglar orqali ham mijoz ismini oshkor qilmaymiz.
            #
            # "shablonlar" esa beriladi: bu taklifnomaga umuman aloqasi
            # yo'q, ochiq katalog ma'lumoti. Sahifa ular bilan nima
            # qilishi — faollashtirilmagan.html boshidagi izohda.
            return render(
                request,
                "taklif/faollashtirilmagan.html",
                {"shablonlar": Shablon.objects.filter(ommaviy=True).order_by("?")[:3]},
            )

    # Ko'rishlar sonini race-condition'siz oshirish — LEKIN faqat shu
    # brauzer/sessiya bu taklifnomani BIRINCHI marta ko'rganda. Aks holda
    # bitta odam sahifani bir necha marta qayta ochsa/yangilasa, har safar
    # alohida ko'rish deb hisoblanib, statistika haqiqiy auditoriyadan
    # sezilarli darajada oshib ketardi.
    korilgan_sluglar = request.session.get(KORISH_SESSIYA_KALITI, [])
    if taklifnoma.slug not in korilgan_sluglar:
        Taklifnoma.objects.filter(pk=taklifnoma.pk).update(korishlar=F("korishlar") + 1)
        korilgan_sluglar.append(taklifnoma.slug)
        request.session[KORISH_SESSIYA_KALITI] = korilgan_sluglar[-200:]
        request.session.modified = True

    if mehmon and not mehmon.korilgan:
        Mehmon.objects.filter(pk=mehmon.pk).update(
            korilgan=True, korilgan_vaqt=timezone.now()
        )

    # Tilaklar — keladi/kelmaydi holatidan qat'i nazar ko'rsatiladi (masalan
    # "kela olmayman, lekin tabriklayman" ham juda tabiiy holat), faqat
    # "tilak" maydoni bo'sh bo'lmagan VA mezbon tomonidan tasdiqlangan
    # javoblar — havolani bilgan har kim (masalan sobiq sevgilisi) yomon
    # niyat bilan yozib qo'yishi mumkin, shuning uchun mezbon tasdiqlamaguncha
    # ommaga ko'rinmaydi (qarang: statistika sahifasi, "tilak_tasdiqlash").
    tilaklar = taklifnoma.javoblar.exclude(tilak="").filter(
        tilak_tasdiqlangan=True
    ).order_by("-yaratilgan")

    context = {
        "taklifnoma": taklifnoma,
        "mehmon": mehmon,
        "tilaklar": tilaklar,
        "rasmlar": taklifnoma.rasmlar.all(),
        "admin_telegram": _admin_telegram(),
        # Taftish topilmasi: taklifnoma faollashtirilgach (tolangan=True),
        # pastdagi "mijoz paneli" (Yoqdi/Qayta yaratish/Mening taklifnomalarim)
        # butunlay yashirilib qolardi — natijada mijozning O'ZI taklifnomasini
        # ochib ko'rgach, saytga qaytishning HECH QANDAY yo'li qolmasdi. Endi
        # shu brauzer sessiyasi shu taklifnomani yaratgan bo'lsa (SESSIYA_KALITI
        # ro'yxatida bo'lsa), faollashtirilgandan keyin ham qaytish havolasi
        # ko'rsatiladi — lekin faqat mijozning o'ziga, mehmonlarga emas.
        "mening_taklifnomam": taklifnoma.slug in request.session.get(SESSIYA_KALITI, []),
        # Marosim sanasi allaqachon o'tib ketgan bo'lsa, mehmonlarga "kelasizmi?"
        # deb so'rash ma'nosiz (va noqulay) bo'lib qoladi — bu holatda RSVP
        # formasi shablonda yashiriladi (qarang: _bolimlar.html).
        "marosim_otgan": taklifnoma.sana < timezone.now(),
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


# Ulashish kartochkasi javobining brauzer/CDN keshi.
#
# Odatiy holat — bir kun: taklifnoma kartochkasi mazmuni o'zgarmaguncha
# bir xil bo'lib qolaveradi.
#
# FAOL_EMAS_KESH_SONIYA esa ATAYLAB qisqa. Sabab amalda ko'rindi: sayt
# Cloudflare orqali ishlaydi va u "public, max-age=86400" ni ko'rib
# rasmni O'Z chekkasida bir kunga saqlab qo'yadi. Faollashtirilmagan
# taklifnoma uchun manzil bir xil bo'lib qoladi ("/ulashish/<slug>.jpg"),
# faqat JAVOB o'zgaradi — to'lov tasdiqlangach reklama kartochkasi
# o'rniga haqiqiysi qaytishi kerak. Uzoq muddat bilan Cloudflare
# to'lovdan keyin ham bir kungacha eski (reklama) rasmni tarqatib
# turardi — ya'ni mijoz havolani mehmonlarga tarqatayotgan aynan o'sha
# daqiqada. Besh daqiqa bu oynani amalda yopadi; haqiqiy kartochkaga
# o'tgach yana to'liq muddat ishlaydi.
KESH_SONIYA = 60 * 60 * 24
FAOL_EMAS_KESH_SONIYA = 60 * 5


def ulashish_kartochkasi(request, slug):
    """Taklifnoma havolasi ulashilganda chiqadigan oldindan ko'rinish rasmi.

    Bu manzilga MEHMON emas, ijtimoiy tarmoqning O'ZI (Telegram, WhatsApp,
    Facebook robotlari) kiradi — sahifadagi "og:image" shu yerni ko'rsatadi.
    Shu sababli:

      * til so'rovdagi "?t=" dan olinadi. Robotda mehmonning sessiyasi ham,
        cookie'si ham yo'q, ya'ni LocaleMiddleware to'g'ri tilni aniqlay
        olmaydi — sahifa qaysi tilda chizilgan bo'lsa, o'sha til manzilga
        yozib yuboriladi (base.html'ga qarang);
      * javob uzoq muddatga keshlanadi — bitta havola yuzlab marta
        ulashiladi;
      * to'lov tasdiqlanmagan taklifnomada ISMLAR CHIQMAYDI — uning
        o'rniga brend kartochkasi qaytadi (pastdagi izohga qarang).
    """
    taklifnoma = get_object_or_404(
        Taklifnoma.objects.select_related("shablon"), slug=slug
    )
    til = _ulashish_tili(request)

    # Sahifadagi himoyaning AYNAN o'zi (yuqoridagi "_taklifnoma_sahifasi"ga
    # qarang): to'lov tasdiqlanmagan taklifnomaning ismi/sanasi begonaga
    # ko'rinmasligi kerak, va u yerda bu hatto meta teglar darajasida ham
    # berkitilgan. Kartochka esa o'sha ma'lumotning O'ZI — ya'ni bu yerda
    # ham xuddi shu shart bo'lishi shart, aks holda slugni bilgan odam
    # sahifada berkitilgan ismni rasmdan o'qib olardi.
    #
    # Xato (404) emas, BREND kartochkasi qaytariladi: bunday havola
    # baribir kimgadir yuboriladi, va o'sha daqiqada Telegramda "bu
    # taklifnoma hali faol emas" degan tushuntirish bilan saytning o'zi
    # ko'ringani — chalkashlikni ham yo'qotadi, biz uchun reklama ham
    # bo'ladi. Mijozning o'zi (sessiyasida shu slug bor) haqiqiy
    # kartochkani ko'radi — u o'z taklifnomasini oldindan sinab ko'rishi
    # kerak.
    if not taklifnoma.tolangan:
        if taklifnoma.slug not in request.session.get(SESSIYA_KALITI, []):
            return _rasm_javobi(reklama_kartochkasi(til), FAOL_EMAS_KESH_SONIYA)

    return _rasm_javobi(kartochka(taklifnoma, til))


def ulashish_reklama(request):
    """Faollashtirilmagan taklifnoma sahifasining oldindan ko'rinishi.

    Barcha shunday havolalar uchun bitta rasm — shu sabab slug'siz,
    alohida manzil (aks holda har bir faollashtirilmagan taklifnoma
    uchun alohida kesh yozuvi paydo bo'lardi, mazmuni esa bir xil).
    """
    return _rasm_javobi(reklama_kartochkasi(_ulashish_tili(request)))


def _ulashish_tili(request):
    til = request.GET.get("t", "")
    return til if til in dict(settings.LANGUAGES) else settings.LANGUAGE_CODE


def _rasm_javobi(baytlar, muddat=KESH_SONIYA):
    javob = HttpResponse(baytlar, content_type="image/jpeg")
    javob["Cache-Control"] = f"public, max-age={muddat}"
    return javob


def _namuna_manzili(shablon_kod, marosim_turi=""):
    manzil = reverse("taklif:namuna", kwargs={"shablon_kod": shablon_kod})
    if marosim_turi:
        manzil = f"{manzil}?marosim={quote(marosim_turi)}"
    return manzil


def namuna(request, shablon_kod):
    """Ochib ko'rish mumkin bo'lgan namuna taklifnoma.

    Mijoz to'lashdan — hatto forma to'ldirishdan ham — oldin mahsulotni
    to'liq, ishlaydigan holida ko'radi: parda ochiladi, musiqa yangraydi,
    sanoq ishlaydi, RSVP formasi javob beradi.

    Bazada hech qanday yozuv yaratilmaydi — sababi namuna.py boshidagi
    izohda.
    """
    shablon = get_object_or_404(Shablon, kod=shablon_kod, ommaviy=True)
    marosim_turi = marosim_tanlash(shablon, request.GET.get("marosim", "").strip())
    taklifnoma = namuna_taklifnomasi(shablon, marosim_turi, _sayt_musiqasi())

    # Mijozning o'z tilagi ro'yxatning ENG TEPASIDA turadi — u aynan
    # o'zinikini izlaydi.
    tilaklar = tayyor_tilaklar(marosim_turi)
    oziniki = sessiyadagi_tilak(request, shablon.kod)
    if oziniki is not None:
        tilaklar.insert(0, oziniki)

    context = {
        "taklifnoma": taklifnoma,
        "mehmon": None,
        "tilaklar": tilaklar,
        "rasmlar": [],
        "admin_telegram": _admin_telegram(),
        "mening_taklifnomam": False,
        "marosim_otgan": False,
        # Shablonlardagi namunaga xos farqlar shu bayroq orqali:
        # yuqoridagi "bu namuna" qatori va RSVP formasining manzili.
        "namuna": True,
        "namuna_shablon_kod": shablon.kod,
        "namuna_marosim_turi": marosim_turi,
        "rsvp_manzili": reverse(
            "taklif:namuna_rsvp", kwargs={"shablon_kod": shablon.kod}
        ),
    }
    return render(request, _shablon_fayli(shablon.kod), context)


@require_POST
def namuna_rsvp(request, shablon_kod):
    """Namunadagi RSVP — javob bazaga emas, sessiyaga yoziladi.

    Mijoz o'z tilagini yozib, uni darhol tilaklar ro'yxatida ko'radi;
    boshqa hech kim ko'rmaydi. Nega aynan shunday — namuna.py boshidagi
    izohga qarang.
    """
    shablon = get_object_or_404(Shablon, kod=shablon_kod, ommaviy=True)
    ism = _postdan_kesib_olish(request, "ism", 100)
    tilak = _postdan_kesib_olish(request, "tilak", 500)
    marosim_turi = marosim_tanlash(shablon, request.POST.get("marosim", "").strip())

    if not ism:
        messages.error(request, _("Iltimos, ismingizni kiriting."))
    elif tilak:
        sessiyaga_tilak_yoz(request, shablon.kod, ism, tilak)
        messages.success(
            request,
            _("Tilagingiz namunaga qo'shildi — uni faqat siz ko'rasiz."),
        )
    else:
        messages.success(request, _("Javobingiz uchun rahmat!"))

    return redirect(_namuna_manzili(shablon.kod, marosim_turi))


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


def _postdan_kesib_olish(request, kalit, maks_uzunlik):
    """POST maydonini o'qiydi va modeldagi max_length'ga mos ravishda kesadi.

    DIQQAT: bu yerda ModelForm ishlatilmagani uchun Django'ning odatiy
    uzunlik tekshiruvi ishlamaydi — agar mehmon maydonga model ruxsat
    etganidan uzunroq matn kiritsa, SQLite (lokal) buni sezmaydi, lekin
    PostgreSQL (production) "value too long" xatosi bilan butun so'rovni
    rad etadi va mehmon RSVP yubora olmay qoladi. Shu uchun har bir
    maydonni saqlashdan oldin qat'iy kesib olamiz — xuddi shu naqsh
    boshqa joylarda (masalan slug, statistika_token) allaqachon qo'llanilgan.
    """
    return request.POST.get(kalit, "").strip()[:maks_uzunlik]


@require_POST
def rsvp_submit(request, slug):
    """Mehmon RSVP formasini yuborishi.

    Agar mehmon shaxsiy link orqali kirgan bo'lsa (mehmon berilgan), forma
    qayta yuborilganda (masalan sahifa yangilansa, orqaga qaytib qayta
    bosilsa) YANGI qator qo'shilmaydi — mavjud javobi yangilanadi. Aks holda
    (mehmon bir necha marta "kelaman" deb yuborsa) mehmonlar soni haqiqiy
    sondan bir necha barobar ko'p bo'lib chiqar edi (RSVP.Meta'dagi
    UniqueConstraint shuni bazada ham kafolatlaydi).

    Shaxsiy linksiz (umumiy sahifadan) yuborilganda mehmon identifikatsiyasi
    yo'q — shu brauzer sessiyasi orqali "eng oxirgi javobim shu edi" deb
    eslab qolamiz, shunda oddiy qayta yuborish (masalan tugmani ikki marta
    bosish) baribir bitta yozuvni yangilaydi, ikkinchi yozuv qo'shilmaydi.
    """
    taklifnoma = get_object_or_404(Taklifnoma, slug=slug, faol=True)

    ism = _postdan_kesib_olish(request, "ism", 100)
    keladi = request.POST.get("keladi") == "ha"
    izoh = _postdan_kesib_olish(request, "izoh", 300)
    tilak = _postdan_kesib_olish(request, "tilak", 500)
    mehmon_slug = request.POST.get("mehmon_slug", "").strip()
    try:
        mehmonlar_soni = int(request.POST.get("mehmonlar_soni", 1))
    except ValueError:
        mehmonlar_soni = 1
    mehmonlar_soni = max(1, min(5, mehmonlar_soni))

    mehmon = None
    if mehmon_slug:
        mehmon = Mehmon.objects.filter(taklifnoma=taklifnoma, slug=mehmon_slug).first()

    if not ism:
        messages.error(request, _("Iltimos, ismingizni kiriting."))
    else:
        qiymatlar = {
            "ism": ism,
            "keladi": keladi,
            "mehmonlar_soni": mehmonlar_soni,
            "izoh": izoh,
            "tilak": tilak,
        }

        if mehmon is not None:
            eski_yozuv = RSVP.objects.filter(taklifnoma=taklifnoma, mehmon=mehmon).first()
        else:
            sessiya_kaliti = f"rsvp_yozuv_id:{taklifnoma.slug}"
            eski_id = request.session.get(sessiya_kaliti)
            eski_yozuv = (
                RSVP.objects.filter(pk=eski_id, taklifnoma=taklifnoma, mehmon__isnull=True).first()
                if eski_id
                else None
            )

        # Tilak matni yangi yoki o'zgargan bo'lsa — qayta tasdiqlash talab
        # qilinadi. Aks holda: mezbon bir marta bitta matnni tasdiqlagan
        # bo'lsa-yu, mehmon (yoki uning linkidan foydalangan boshqa kimdir)
        # keyinroq matnni butunlay boshqasiga — masalan haqoratga —
        # almashtirsa, eski tasdiq bilan avtomatik ochiq qolib ketmasligi
        # kerak.
        if eski_yozuv is None or eski_yozuv.tilak != tilak:
            qiymatlar["tilak_tasdiqlangan"] = False

        if mehmon is not None:
            # Shaxsiy link — (taklifnoma, mehmon) juftligi bo'yicha bitta
            # javob kafolatlanadi (bazadagi UniqueConstraint bilan birga).
            RSVP.objects.update_or_create(
                taklifnoma=taklifnoma, mehmon=mehmon, defaults=qiymatlar
            )
        else:
            # Shaxsiy linksiz — sessiyada saqlangan oxirgi javob yozuvini
            # yangilaymiz (agar bo'lsa), aks holda yangisini yaratamiz.
            if eski_yozuv is not None:
                for maydon, qiymat in qiymatlar.items():
                    setattr(eski_yozuv, maydon, qiymat)
                eski_yozuv.save()
            else:
                yangi_yozuv = RSVP.objects.create(taklifnoma=taklifnoma, mehmon=None, **qiymatlar)
                request.session[sessiya_kaliti] = yangi_yozuv.pk
                request.session.modified = True
        messages.success(request, _("Javobingiz uchun rahmat!"))

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
        {"taklifnomalar": taklifnomalar},
    )


@require_POST
def taklifnoma_ochirish(request, slug):
    """Mijoz o'zi ushbu brauzer sessiyasida yaratgan taklifnomani o'chiradi.

    Faqat sessiyada turgan (ya'ni shu brauzerda o'zi yaratgan) taklifnomalarni
    o'chirish mumkin — havolani bilib olib boshqa birovning taklifnomasini
    o'chirib qo'yishning oldini olish uchun.

    Ikki xil holat farqlanadi:
    — Hali TO'LANMAGAN qoralama: mehmonlarga hech qachon yuborilmagan, RSVP
      bo'lishi mumkin emas — xavfsiz, darhol butunlay o'chiriladi (rasmlar ham
      CASCADE orqali birga o'chadi; R2/S3'dagi fayllarning o'zi hozircha qolib
      ketadi — bu alohida tozalash vazifasi, shu funksiya doirasida emas).
    — FAOLLASHTIRILGAN (to'langan) taklifnoma: mehmonlarga yuborilgan va RSVP
      javoblari bo'lishi mumkin — bitta xato bosish bilan butunlay yo'qolib
      ketmasligi uchun darhol o'chirilmaydi, "chiqindilar"ga o'tkaziladi
      (faol=False — mehmonlarga xuddi "muddati tugagan" kabi ko'rinadi,
      ochirilgan_vaqt=hozir). CHIQINDI_SAQLASH_KUNLARI kun ichida admin
      panelidan tiklash mumkin; shundan keyin `eski_chiqindilarni_tozalash`
      boshqaruv buyrug'i butunlay o'chiradi.
    """
    sluglar = request.session.get(SESSIYA_KALITI, [])
    if slug not in sluglar:
        messages.error(request, _("Bu taklifnomani o'chira olmaysiz."))
        return redirect("taklif:mening_taklifnomalarim")

    taklifnoma = get_object_or_404(Taklifnoma, slug=slug)
    nomi = taklifnoma.sarlavha

    if taklifnoma.tolangan:
        taklifnoma.faol = False
        taklifnoma.ochirilgan_vaqt = timezone.now()
        taklifnoma.save(update_fields=["faol", "ochirilgan_vaqt"])
        xabar = _(
            '"%(nomi)s" taklifnomasi o\'chirildi. Bu faollashtirilgan '
            "taklifnoma bo'lgani uchun ma'lumotlari %(kun)s kun davomida "
            "saqlanadi — agar xato bosgan bo'lsangiz, administratorga "
            "murojaat qiling."
        ) % {"nomi": nomi, "kun": CHIQINDI_SAQLASH_KUNLARI}
    else:
        taklifnoma.delete()
        xabar = _('"%(nomi)s" taklifnomasi o\'chirildi.') % {"nomi": nomi}

    sluglar.remove(slug)
    request.session[SESSIYA_KALITI] = sluglar
    request.session.modified = True

    messages.success(request, xabar)
    return redirect("taklif:mening_taklifnomalarim")


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
    admin_username = _admin_telegram().lstrip("@")
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


@require_POST
def mehmon_qoshish(request, token):
    """Mijoz statistika sahifasining o'zidan turib (admin panelga kirmasdan)
    mehmon uchun shaxsiy link yaratadi.

    Bu — token orqali maxfiy sahifa (statistika sahifasi bilan bir xil
    xavfsizlik modeli): tokenni bilgan kishi mijozning o'zi deb hisoblanadi,
    alohida login talab qilinmaydi.
    """
    taklifnoma = get_object_or_404(Taklifnoma, statistika_token=token)
    ism = _postdan_kesib_olish(request, "ism", 100)
    if not ism:
        messages.error(request, _("Iltimos, mehmon ismini kiriting."))
    else:
        Mehmon.objects.create(taklifnoma=taklifnoma, ism=ism)
        messages.success(request, _('"%(ism)s" uchun shaxsiy link yaratildi.') % {"ism": ism})
    return redirect("taklif:statistika", token=token)


@require_POST
def mehmon_ochirish(request, token, mehmon_id):
    """Mijoz xato qo'shgan mehmonni statistika sahifasidan turib o'chiradi."""
    taklifnoma = get_object_or_404(Taklifnoma, statistika_token=token)
    Mehmon.objects.filter(pk=mehmon_id, taklifnoma=taklifnoma).delete()
    messages.success(request, _("Mehmon o'chirildi."))
    return redirect("taklif:statistika", token=token)


@require_POST
def tilak_tasdiqlash(request, token, javob_id):
    """Mijoz statistika sahifasidan turib bitta tilakni hammaga ochiq
    qiladi (yoki qaytadan yashiradi — tugma ikkala holatda ham shu bitta
    manzilga POST qiladi, "almashtirish" mantig'i bilan)."""
    taklifnoma = get_object_or_404(Taklifnoma, statistika_token=token)
    javob = get_object_or_404(RSVP, pk=javob_id, taklifnoma=taklifnoma)
    javob.tilak_tasdiqlangan = not javob.tilak_tasdiqlangan
    javob.save(update_fields=["tilak_tasdiqlangan"])
    if javob.tilak_tasdiqlangan:
        messages.success(request, _("Tilak endi taklifnoma sahifasida hammaga ko'rinadi."))
    else:
        messages.success(request, _("Tilak yashirildi — endi faqat sizga ko'rinadi."))
    return redirect("taklif:statistika", token=token)
