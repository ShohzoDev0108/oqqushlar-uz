# -*- coding: utf-8 -*-
"""Har bir til uchun sana formati (FORMAT_MODULE_PATH).

MUAMMO. Shablonlarda sana `date:"d-F, Y"` deb qat'iy yozilgan edi. `F` —
oyning BOSH KELISHIKDAGI nomi ("Oktyabr"). O'zbek tilida bu to'g'ri, lekin
rus tilida sana ichida oy QARATQICH kelishigida keladi: to'g'risi
"12 октября 2026", bizda esa "12-Октябрь, 2026" chiqardi — rus tilida
so'zlashuvchi mehmon buni darrov xato deb ko'radi.

YECHIM. Django'da har bir til uchun alohida format moduli bo'lishi mumkin
(FORMAT_MODULE_PATH sozlamasi, config/settings.py'da ko'rsatilgan).
Shablonlarda endi format o'rniga `date:"DATE_FORMAT"` yoziladi — Django
mehmon tanlagan tilga qarab shu papkadagi tegishli formatni oladi.

FORMAT BELGILARI:
    d — kun, ikki xonali ("05")        j — kun, nolsiz ("5")
    F — oy, bosh kelishikda            E — oyning sana ichidagi shakli
    Y — yil, to'rt xonali

`E` aynan shu maqsad uchun mavjud: rus va tojik tillarida u qaratqich
shaklni beradi ("октября"), qolgan tillarda esa `F` bilan bir xil natija
qaytaradi — ya'ni zarar qilmaydi.

NEGA O'ZBEK TILI BOSHQACHA. O'zbekchada sana "12-oktabr, 2026" ko'rinishida
yoziladi — chiziqcha va vergul bilan. Shuning uchun uz va kaa uchun eski
format saqlab qolindi, ya'ni asosiy tilda hech narsa o'zgarmaydi.

NIMAGA TA'SIR QILADI. DATE_FORMAT butun loyihada ishlatiladi — taklifnoma
sahifasi, ulashish kartochkasi va admin panelidagi sana ustunlari ham shu
formatni oladi. Bu ataylab: sana hamma joyda bir xil ko'rinishi kerak.
"""
