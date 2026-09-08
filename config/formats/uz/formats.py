# -*- coding: utf-8 -*-
"""O'zbek tili uchun sana formati.

Django har bir til uchun o'z formatini taklif qiladi, lekin ular bizga
to'g'ri kelmadi (masalan rus tilida "12 октября 2026 г." — oxiridagi "г."
taklifnomada ortiqcha, ingliz tilida esa "Oct. 12, 2026" — qisqartma bilan).
Shuning uchun formatni o'zimiz belgilaymiz. Batafsil: config/formats/__init__.py
"""

# Natija: "12-Oktabr, 2026"
DATE_FORMAT = "d-F, Y"
