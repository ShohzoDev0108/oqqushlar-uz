"""Testlar uchun umumiy yordamchi funksiyalar (fixture'lar)."""
from taklif.models import Shablon


def shablon_yarat(kod="suzani", ommaviy=True, narx=0):
    shablon, _ = Shablon.objects.get_or_create(
        kod=kod, defaults={"nomi": kod.capitalize(), "narx": narx, "ommaviy": ommaviy}
    )
    return shablon


# TaklifnomaYaratishForm to'ldirish uchun eng kam (majburiy) maydonlar.
ASOSIY_FORMA_MAYDONLARI = {
    "marosim_turi": "sunnat_toy",  # IKKI_ISMLI_MAROSIM_TURLARI'ga kirmaydi -> ism_2 shart emas
    "ism_1": "Sardor",
    "sana": "2027-05-20T18:00",
}
