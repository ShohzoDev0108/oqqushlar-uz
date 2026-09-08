# -*- coding: utf-8 -*-
"""Google uchun sayt xaritasi (sitemap.xml).

NEGA KERAK. Qidiruv tizimi sahifalarni havolalar bo'ylab kezib topadi.
Sayt xaritasi esa unga "mana, mening sahifalarim" deb TO'G'RIDAN-TO'G'RI
ro'yxat beradi — ayniqsa yangi saytda, tashqi havolalar hali kam
bo'lganda, bu indekslanishni sezilarli tezlashtiradi.

NIMA KIRADI. Faqat OMMAVIY va MAZMUNLI sahifalar:
  * saytning o'z sahifalari (bosh sahifa, katalog, narxlar va h.k.);
  * har bir ommaviy dizaynning NAMUNA sahifasi — bular eng qimmatli
    qismi: yigirmata alohida sahifa, har biri to'liq ishlaydigan
    taklifnoma. Odam "beshik to'yi taklifnomasi" deb qidirsa, aynan
    shular chiqishi kerak.

NIMA KIRMAYDI VA NEGA:
  * mijozlarning taklifnomalari — ularda ism va marosim sanasi bor;
  * "Mening taklifnomalarim", "Tayyor", statistika — shaxsiy sahifalar;
  * taklifnoma yaratish formalari — ular qidiruvdan kelgan odam uchun
    kirish nuqtasi emas, va yigirmata bir xil forma sahifasi qidiruv
    tizimi uchun "takroriy mazmun" bo'lib ko'rinadi.

DOMEN QAYERDAN OLINADI. "django.contrib.sites" o'rnatilmagan, shuning
uchun Django so'rovning o'z hostini ishlatadi (RequestSite) — ya'ni
qo'shimcha sozlama ham, migratsiya ham kerak emas.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Shablon


class SaytSahifalari(Sitemap):
    """Saytning o'zgarmaydigan sahifalari."""

    protocol = "https"

    # Ustuvorlik (priority) — Google uchun majburiy ko'rsatma emas,
    # shunchaki "men uchun qaysi biri muhimroq" degan maslahat. Bosh
    # sahifa va katalog eng yuqorida, chunki mijoz yo'li aynan shulardan
    # boshlanadi.
    SAHIFALAR = [
        ("taklif:bosh_sahifa", 1.0, "weekly"),
        ("taklif:shablon_tanlash", 0.9, "weekly"),
        ("taklif:narxlar", 0.8, "monthly"),
        ("taklif:savol_javob", 0.7, "monthly"),
        ("taklif:biz_haqimizda", 0.6, "monthly"),
        ("taklif:boglanish", 0.6, "monthly"),
    ]

    def items(self):
        return self.SAHIFALAR

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]

    def changefreq(self, item):
        return item[2]


class NamunaSahifalari(Sitemap):
    """Har bir ommaviy dizaynning "ochib ko'rish" namunasi.

    Bu — saytdagi eng ko'p sahifali va eng mazmunli qism: yigirmata
    alohida manzil, har birida to'liq ishlaydigan taklifnoma.
    """

    protocol = "https"
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Shablon.objects.filter(ommaviy=True).order_by("kod")

    def location(self, shablon):
        return reverse("taklif:namuna", kwargs={"shablon_kod": shablon.kod})


SAYT_XARITALARI = {
    "sahifalar": SaytSahifalari,
    "namunalar": NamunaSahifalari,
}
