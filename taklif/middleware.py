from django.conf import settings
from django.utils import translation

# Faqat mezbon (taklifnoma egasi) ko'radigan sahifalar — mehmonlarga
# ulashiladigan taklifnoma sahifalarining o'zi bu ro'yxatda EMAS (ular hali
# ham to'liq avtomatik ko'p tillilikdan foydalanadi).
MEZBON_MANZIL_BOSHLARI = (
    "/statistika/",
    "/mening-taklifnomalarim",
    "/tayyor/",
)


class MezbonTiliniStandartlashMiddleware:
    """Mezbonga tegishli sahifalarni (statistika, "Mening taklifnomalarim",
    "Taklifnomangiz tayyor!") — hech qanday til aniq tanlanmagan bo'lsa —
    har doim o'zbek tilida ko'rsatadi.

    Taftish topilmasi: mijoz taklifnomani odatda o'zbek tilida yaratadi,
    keyin "Statistika" havolasini boshqa qurilma yoki ilovada (masalan
    Telegram'ning ichki brauzerida) ochsa — o'sha yerda mijozning avval
    tanlagan tili (Django bu tanlovni FAQAT cookie orqali eslab qoladi,
    sessiya orqali emas) yo'q, shuning uchun LocaleMiddleware o'sha
    qurilmaning "Accept-Language" sarlavhasiga qarab tilni tasodifan
    boshqa (masalan rus yoki ingliz) tilga o'zgartirib qo'yardi.

    DIQQAT: agar mijoz shu sahifaning o'zida til tugmasidan ANIQ boshqa
    tilni tanlagan bo'lsa (bu holda cookie o'rnatiladi), bu middleware
    aralashmaydi — mijozning o'z tanlovi doim ustun turadi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(MEZBON_MANZIL_BOSHLARI):
            if settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
                translation.activate(settings.LANGUAGE_CODE)
                request.LANGUAGE_CODE = settings.LANGUAGE_CODE
        return self.get_response(request)


class AdminTiliniMajburlashMiddleware:
    """Boshqaruv panelini har doim o'zbek tilida ko'rsatadi.

    Django'ning odatiy LocaleMiddleware'i tashrif buyuruvchi brauzerining
    "Accept-Language" sarlavhasiga (yoki avval tanlangan til cookie'siga)
    qarab tilni tanlaydi. Bu, masalan, xodimning brauzeri ingliz tiliga
    sozlangan bo'lsa, boshqaruv panelini ingliz tilida ko'rsatishi mumkin.

    Boshqaruv paneli — ichki, xodimlar uchun mo'ljallangan vosita, mehmonlar
    uchun emas (mehmon interfeysi hali ham LocaleMiddleware orqali 8 ta
    tilda ishlaydi). Shuning uchun bu middleware LocaleMiddleware'dan KEYIN
    ishlab, faqat boshqaruv paneli manzillari uchun tilni majburan "uz"ga
    o'rnatadi — xodimning shaxsiy brauzer sozlamalaridan qat'i nazar.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/" + settings.ADMIN_URL_YOLI):
            translation.activate("uz")
            request.LANGUAGE_CODE = "uz"
        return self.get_response(request)
