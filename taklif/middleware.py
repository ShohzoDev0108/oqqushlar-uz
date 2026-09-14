from django.conf import settings
from django.utils import translation


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
