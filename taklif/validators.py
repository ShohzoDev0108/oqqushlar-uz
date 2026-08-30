"""Mijoz o'zi yuklaydigan fayllar (musiqa, rasm) uchun umumiy tekshiruvchilar.

DIQQAT: bu tekshiruvchilar faqat ModelForm orqali (masalan
TaklifnomaYaratishForm) to'ldirilgan maydonlarda avtomatik ishlaydi —
Django validatorlar model maydoniga biriktirilgan bo'lsa ham, ular faqat
full_clean() chaqirilganda (ya'ni forma tasdiqlanganda) ishga tushadi.
Agar biror joyda Model.objects.create() to'g'ridan-to'g'ri chaqirilsa
(masalan TaklifnomaRasm — ko'p fayl yuklash formasi bo'lmagani uchun),
bu validatorlar o'zi ishlamaydi — o'sha joyda alohida, qo'lda chaqirish
kerak (taklif/views.py'dagi _rasmlar_xatosini_tekshir() ga qarang).
"""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class FaylHajmiValidator:
    """Yuklangan faylning hajmi berilgan chegaradan (MB) oshmasligini tekshiradi."""

    def __init__(self, maks_mb):
        self.maks_mb = maks_mb

    def __call__(self, fayl):
        maks_bayt = self.maks_mb * 1024 * 1024
        if fayl.size > maks_bayt:
            raise ValidationError(
                _(
                    "Fayl hajmi %(maks)s MB dan katta bo'lmasligi kerak "
                    "(yuklangan fayl: %(hajm).1f MB)."
                ),
                params={"maks": self.maks_mb, "hajm": fayl.size / (1024 * 1024)},
            )

    def __eq__(self, other):
        return isinstance(other, FaylHajmiValidator) and self.maks_mb == other.maks_mb
