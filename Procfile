# ESKIRGAN (2026-09-14): bu fayl Render.com/Heroku kabi platformalar uchun
# yozilgan edi. Loyiha hozir Hetzner VPS'da systemd + gunicorn + nginx
# orqali ishlaydi (dizayn/server/ papkasiga qarang) — bu fayl endi HECH
# QANDAY platforma tomonidan o'qilmaydi. Faqat tarixiy murojaat uchun
# saqlanmoqda, xavfsiz o'chirish mumkin.
web: gunicorn config.wsgi --log-file -
release: python manage.py migrate --noinput
