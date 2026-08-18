from django.urls import path

from . import views

app_name = "taklif"

urlpatterns = [
    path("", views.bosh_sahifa, name="bosh_sahifa"),
    path("yaratish/", views.shablon_tanlash, name="shablon_tanlash"),
    path("yaratish/<slug:shablon_kod>/", views.yaratish, name="yaratish"),
    path("tayyor/<slug:slug>/", views.yaratildi, name="yaratildi"),
    path("statistika/<str:token>/", views.statistika, name="statistika"),
    path(
        "mening-taklifnomalarim/",
        views.mening_taklifnomalarim,
        name="mening_taklifnomalarim",
    ),
    path("<slug:slug>/rsvp/", views.rsvp_submit, name="rsvp_submit"),
    path("<slug:slug>/yoqdi/", views.yoqdi, name="yoqdi"),
    # Mehmon uchun shaxsiy link — "rsvp/"/"yoqdi/" literal manzillaridan keyin,
    # umumiy "<slug:slug>/" manzilidan oldin turishi shart.
    path("<slug:slug>/<slug:mehmon_slug>/", views.mehmon_korish, name="mehmon_korish"),
    path("<slug:slug>/", views.korish, name="korish"),
]
