"""
Faqat testlarni diagnostika qilish uchun VAQTINCHALIK sozlama fayli.

Django test klienti biror view xato (exception) tashlaganda, xato
sahifasini (500.html yoki debug texnik traceback) render qilishga
urinadi. Aynan shu render bosqichida joriy Python 3.14 + Django 5.0.14
muhitida ichki `Context.__copy__` xatosi yuz beryapti va bu haqiqiy
xatoni butunlay yashiryapti (--debug-mode bilan ham).

DEBUG_PROPAGATE_EXCEPTIONS = True — Django'ga hech qanday xato sahifa
render qilmasdan, asl xatoni to'g'ridan-to'g'ri yuqoriga otib yuborishni
buyuradi. Shu tufayli test natijasida endi yashiringan emas, ASL xato
va uning to'liq traceback'i ko'rinadi.

Ishlatilishi:
    python manage.py test taklif --settings=config.settings_test

Bu faqat diagnostika uchun vaqtinchalik fayl — muammo topilgach
o'chirib tashlash mumkin, production yoki oddiy local ishlatishga
aloqasi yo'q.
"""
from .settings import *  # noqa: F401,F403

DEBUG_PROPAGATE_EXCEPTIONS = True

# ---------------------------------------------------------------------------
# ASOSIY TUZATISH: Django test klienti har bir render qilingan shablon uchun
# `Context`'ni nusxalaydi (test tekshiruvlarida response.context ishlatish
# uchun). Bu nusxalash `django.template.context.BaseContext.__copy__`
# ichida `copy(super())` degan usul bilan amalga oshadi. Python 3.14'da
# `copy()` funksiyasi `super` proksi obyektini haqiqiy nusxalamasdan, xuddi
# shu proksi obyektning o'zini qaytarib yuboradi — natijada `dicts`
# atributi yo'q bo'lib chiqadi va AttributeError yuz beradi. Bu HAR BIR
# shablon render qilingan testda (hatto xatosiz, muvaffaqiyatli testlarda
# ham) yuz berib, asl natijalarni butunlay yashiryapti.
#
# Pastdagi kod `BaseContext.__copy__`ni buzilgan `copy(super())` usulisiz,
# qo'lda nusxa yaratadigan xavfsiz usul bilan almashtiradi. Faqat shu test
# sozlamasida ishlaydi — production yoki oddiy local ishga aloqasi yo'q.
from django.template.context import BaseContext as _BaseContext


def _bosqich1_xavfsiz_context_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


_BaseContext.__copy__ = _bosqich1_xavfsiz_context_copy

# ---------------------------------------------------------------------------
# IKKINCHI TUZATISH: production sozlamasida `STORAGES["staticfiles"]["BACKEND"]`
# WhiteNoise'ning `CompressedManifestStaticFilesStorage'iga o'rnatilgan. Bu
# backend har bir `{% static %}` uchun `staticfiles.json` manifest faylidan
# haqiqiy (hash-nomli) fayl nomini qidiradi — bu manifest esa faqat
# `python manage.py collectstatic` ishga tushirilgandagina yaratiladi.
#
# Lokal test muhitida hech qachon `collectstatic` ishga tushirilmagan
# (STATIC_ROOT papkasi umuman mavjud emas), shu sababli HAR BIR shablon
# render qilingan test `ValueError: Missing staticfiles manifest entry for
# "..."` xatosi bilan yiqiladi — bu Bosqich 1 kodiga umuman aloqasi yo'q,
# sof lokal test muhiti muammosi.
#
# Pastdagi qator faqat shu test sozlamasida statik fayllar uchun oddiy,
# manifest talab qilmaydigan backend'ga almashtiradi — production yoki
# oddiy local ishga (`runserver`) aloqasi yo'q.
STORAGES["staticfiles"] = {
    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
}
