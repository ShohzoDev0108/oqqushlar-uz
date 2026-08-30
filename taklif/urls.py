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
