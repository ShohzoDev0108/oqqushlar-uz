from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "taklif"

urlpatterns = [
    path("", views.bosh_sahifa, name="bosh_sahifa"),
    # Dizaynlar katalogi. Manzil ataylab "/dizaynlar/" — sahifaning
    # o'zi ham, menyudagi havola ham "Dizaynlar" deb ataladi, oldingi
    # "/yaratish/" esa nomi bilan mazmuni bir-biriga mos kelmasdi.
    # Eski manzil ishlashda davom etadi (mijozlarda saqlangan havolalar,
    # QR kodlar, qidiruv natijalari uchun) — u shu yerga yo'naltiriladi.
    path("dizaynlar/", views.shablon_tanlash, name="shablon_tanlash"),
    path(
        "yaratish/",
        RedirectView.as_view(pattern_name="taklif:shablon_tanlash", permanent=True),
        name="shablon_tanlash_eski",
    ),
    path("biz-haqimizda/", views.biz_haqimizda, name="biz_haqimizda"),
    path("boglanish/", views.boglanish, name="boglanish"),
    path("savol-javob/", views.savol_javob, name="savol_javob"),
    path("yaratish/<slug:shablon_kod>/", views.yaratish, name="yaratish"),
    # Ochib ko'rish mumkin bo'lgan namuna taklifnoma — mijoz mahsulotni
    # to'lashdan oldin to'liq, ishlaydigan holida ko'radi. Bazada hech
    # qanday yozuv yaratmaydi (sababi: namuna.py boshidagi izoh).
    # "<slug:slug>/<slug:mehmon_slug>/" dan OLDIN turishi SHART — aks
    # holda "namuna/sadaf/" mehmon havolasi deb tushunilardi.
    path("namuna/<slug:shablon_kod>/rsvp/", views.namuna_rsvp, name="namuna_rsvp"),
    path("namuna/<slug:shablon_kod>/", views.namuna, name="namuna"),
    path("tayyor/<slug:slug>/", views.yaratildi, name="yaratildi"),
    path("statistika/<str:token>/", views.statistika, name="statistika"),
    path(
        "statistika/<str:token>/mehmon-qoshish/",
        views.mehmon_qoshish,
        name="mehmon_qoshish",
    ),
    path(
        "statistika/<str:token>/mehmon-ochirish/<int:mehmon_id>/",
        views.mehmon_ochirish,
        name="mehmon_ochirish",
    ),
    path(
        "statistika/<str:token>/tilak/<int:javob_id>/",
        views.tilak_tasdiqlash,
        name="tilak_tasdiqlash",
    ),
    path(
        "mening-taklifnomalarim/",
        views.mening_taklifnomalarim,
        name="mening_taklifnomalarim",
    ),
    path(
        "mening-taklifnomalarim/<slug:slug>/ochirish/",
        views.taklifnoma_ochirish,
        name="taklifnoma_ochirish",
    ),
    path("<slug:slug>/rsvp/", views.rsvp_submit, name="rsvp_submit"),
    path("<slug:slug>/yoqdi/", views.yoqdi, name="yoqdi"),
    # Mehmon uchun shaxsiy link — "rsvp/"/"yoqdi/" literal manzillaridan keyin,
    # umumiy "<slug:slug>/" manzilidan oldin turishi shart.
    path("<slug:slug>/<slug:mehmon_slug>/", views.mehmon_korish, name="mehmon_korish"),
    path("<slug:slug>/", views.korish, name="korish"),
]
