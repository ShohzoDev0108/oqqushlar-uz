from django.conf import settings
from django.utils import translation

# Saytning "asosiy" — mijozga tegishli, taklifnoma slug'i bo'lmagan — barcha
# sahifalari: bosh sahifa, taklifnoma yaratish, statistika, "Mening
# taklifnomalarim", "Taklifnomangiz tayyor!" va h.k. Mehmonlarga
# ulashiladigan taklifnoma sahifasining o'zi ("/<slug>/", "/<slug>/rsvp/",
# "/<slug>/<mehmon_slug>/" va h.k.) BU RO'YXATDA ATAYLAB YO'Q — u hali ham
# mehmonning o'z brauzer/qurilma tiliga avtomatik moslashadi (quyida
# batafsil izohlangan).
ASOSIY_SAHIFA_BOSHLARI = (
    "/yaratish",
    "/statistika/",
    "/mening-taklifnomalarim",
    "/tayyor/",
)


class SaytTiliniStandartlashMiddleware:
    """Saytning asosiy (mijozga tegishli, mehmonga ulashilmaydigan)
    sahifalarini — bosh sahifa, taklifnoma yaratish, statistika, "Mening
    taklifnomalarim", "Taklifnomangiz tayyor!" — hech qanday til aniq
    tanlanmagan bo'lsa, har doim o'zbek tilida ko'rsatadi.

    Taftish topilmasi: Django'ning odatiy LocaleMiddleware'i tashrif
    buyuruvchi brauzerining "Accept-Language" sarlavhasiga qarab tilni
    tanlaydi — ko'pchilik O'zbekistondagi foydalanuvchining brauzeri yoki
    operatsion tizimi rus yoki ingliz tiliga sozlangan bo'lishi mumkin,
    natijada sayt birinchi marta ochilganda kutilmaganda boshqa tilda
    ko'rinardi. Endi bu middleware LocaleMiddleware'dan KEYIN ishlab,
    aniq cookie orqali til tanlanmagan bo'lsa, saytning asosiy qismini
    majburan o'zbek tiliga o'rnatadi.

    DIQQAT #1: agar mijoz shu sahifaning o'zida til tugmasidan ANIQ boshqa
    tilni tanlagan bo'lsa (bu holda cookie o'rnatiladi), bu middleware
    aralashmaydi — mijozning o'z tanlovi doim ustun turadi.

    DIQQAT #2: mehmonlarga ulashiladigan taklifnoma sahifasining o'zi
    (ASOSIY_SAHIFA_BOSHLARI'da YO'Q — taklifnoma slug'i har xil bo'lgani
    uchun oldindan ro'yxatga kiritib bo'lmaydi, shuning uchun manfiy
    mantiq bilan — "asosiy sahifa emas" — aniqlanadi) ATAYLAB bu yerga
    kiritilmagan: mehmon o'z brauzeridan (masalan rus tilida sozlangan
    qurilmadan) kirsa, taklifnomani darhol o'z tilida ko'rishi kerak —
    bu foydali, ataylab qilingan xususiyat, uni o'chirib qo'ymaslik kerak.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/" or request.path.startswith(ASOSIY_SAHIFA_BOSHLARI):
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
