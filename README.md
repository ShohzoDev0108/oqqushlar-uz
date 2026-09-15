# Taklifnoma365 — raqamli taklifnoma platformasi

To'y, sunnat to'yi, yubiley, tug'ilgan kun va boshqa marosimlar uchun chiroyli,
ko'p tilli raqamli taklifnomalarni bir necha daqiqada yaratish imkonini
beruvchi Django ilovasi. Mijoz o'zi dizayn tanlaydi, ma'lumotlarini to'ldiradi
va tayyor havolani yaqinlariga ulashadi.

## Asosiy imkoniyatlar

- **15 ta tayyor dizayn** — uch turkumga bo'lingan: *Zamonaviy* (Registon,
  Sodda, Gulbarg, Yulduz, Zumrad, Marmar), *Milliy* (Atlas, Suzani, Zardo'z,
  Chinni, Qozoq, Qirg'iz, Turkman, Tojik) va *Bolalar* (Bolajon). Shablon
  tanlash sahifasida turkum bo'yicha filtr tugmalari bilan.
- **8 tilda interfeys** — o'zbek, rus, ingliz, tojik, qozoq, qirg'iz, turkman,
  qoraqalpoq. Mehmon sahifa yuqorisidagi til tugmasi orqali tanlaydi;
  mijozning o'zi kiritgan ism/matn har doim asl tilida qoladi.
- **3D konvert-ochilish animatsiyasi** va sahifa scroll-animatsiyalari.
- **Til bo'yicha fon musiqasi** — sayt tilini almashtirsa, mos musiqa
  yangraydi; sahifadan-sahifaga o'tishda musiqa to'xtagan joyidan davom etadi.
- **Self-service oqim** — mijoz `/yaratish/` sahifasidan dizayn tanlaydi,
  formani to'ldiradi (ismlar, sana, manzil, matn, sovg'a karta, Telegram
  havola), 4 tagacha rasm yuklaydi — va taklifnoma tayyor.
- **RSVP** — mehmonlar "kelasizmi" formasini to'ldiradi, admin panelda va
  maxfiy statistika sahifasida natijalar ko'rinadi.
- **Shaxsiy mehmon havolalari** — har bir mehmon uchun ismi bilan kutib
  oluvchi alohida havola.
- **Sessiya asosida "Mening taklifnomalarim"** — login talab qilinmaydi.
- **Admin panel** — barcha modellar (Shablon, Taklifnoma, Mehmon, RSVP,
  MusiqaVariant, TaklifnomaRasm) to'liq boshqariladi.

## Texnologiyalar

- Python 3.11+, Django 5.0
- SQLite (development uchun standart; production'da istalgan Django
  qo'llab-quvvatlaydigan bazaga almashtirish mumkin)
- `python-dotenv` — maxfiy sozlamalarni `.env` faylidan o'qish uchun
- Django i18n (gettext) — ko'p tillilik

## Loyiha tuzilishi

```
oqqushlar_project/
├── manage.py
├── requirements.txt
├── .env.example          # .env uchun namuna (haqiqiy maxfiy qiymatsiz)
├── config/                # sozlamalar (settings, urls, wsgi/asgi)
├── locale/                 # 7 tilning tarjima kataloglari (.po/.mo)
├── taklif/                 # asosiy app
│   ├── models.py           # Shablon, Taklifnoma, Mehmon, RSVP, MusiqaVariant, TaklifnomaRasm
│   ├── admin.py
│   ├── forms.py
│   ├── views.py
│   ├── urls.py
│   ├── migrations/
│   └── templates/taklif/
│       └── shablonlar/     # 15 ta dizayn shabloni + umumiy include qismlar
└── templates/               # umumiy base.html
```

## O'rnatish

1. Repozitoriyani klonlang va papkaga o'ting:
   ```
   git clone <repo-havolasi>
   cd oqqushlar_project
   ```
2. Virtual muhit yarating va faollashtiring:
   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   source .venv/bin/activate   # Linux/Mac
   ```
3. Kutubxonalarni o'rnating:
   ```
   pip install -r requirements.txt
   ```
4. `.env` faylini tayyorlang:
   ```
   cp .env.example .env        # Linux/Mac
   copy .env.example .env      # Windows
   ```
   Keyin `.env` ichida `DJANGO_SECRET_KEY` maydonini quyidagi buyruq bilan
   generatsiya qilingan qiymat bilan to'ldiring:
   ```
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Lokal kompyuterda ishlatish uchun boshqa qiymatlarni o'zgartirish shart
   emas (`DJANGO_DEBUG=True` standart holatda ishlaydi).
5. Ma'lumotlar bazasini tayyorlang:
   ```
   python manage.py migrate
   ```
6. Admin foydalanuvchi yarating:
   ```
   python manage.py createsuperuser
   ```
7. Serverni ishga tushiring:
   ```
   python manage.py runserver
   ```
8. Brauzerda oching:
   - Bosh sahifa: http://127.0.0.1:8000/
   - Admin panel: http://127.0.0.1:8000/admin/
   - Dizayn tanlash: http://127.0.0.1:8000/yaratish/

Admin panelda kamida bitta **Shablon** qatori kerak (migratsiyalar 15 ta
tayyor shablonni avtomatik qo'shadi — qo'shimcha qo'lda ish shart emas).

## Tarjimalar bilan ishlash

Yangi matn qo'shsangiz, quyidagicha yangilang:
```
django-admin makemessages -l ru -l en -l tg -l kk -l ky -l tk -l kaa
# .po fayllarni tarjima qiling, so'ng:
django-admin compilemessages
```
(`gettext` paketi kompyuteringizda o'rnatilgan bo'lishi kerak — Windows'da
[GnuWin32 gettext](https://mlocati.github.io/articles/gettext-iconv-windows.html)
yoki WSL orqali.)

## Xavfsizlik — production'ga chiqarishdan oldin

- `.env` faylini **hech qachon** Git'ga qo'shmang — u allaqachon
  `.gitignore`'da, lekin ehtiyot bo'ling.
- Production serverda `.env` ichida `DJANGO_DEBUG=False` va uzun, tasodifiy
  `DJANGO_SECRET_KEY` qo'ying (yuqoridagi buyruq bilan generatsiya qiling).
  `DJANGO_DEBUG=False` bo'lganda standart (haqiqiy bo'lmagan) kalit bilan
  server ishga tushmaydi — bu ataylab qo'yilgan himoya.
- `DJANGO_ALLOWED_HOSTS` ga faqat haqiqiy domeningizni yozing.
- Sayt HTTPS orqali ishlaganda `DJANGO_DEBUG=False` avtomatik ravishda
  HSTS, secure-cookie va boshqa xavfsizlik sarlavhalarini yoqadi
  (`config/settings.py`ga qarang). Agar nginx/caddy kabi teskari-proksi
  orqasida bo'lsangiz, `.env`da `DJANGO_BEHIND_PROXY=1` qo'ying.
- Statik fayllarni yig'ish uchun: `python manage.py collectstatic`.
- Ishlab chiqarishga chiqarishdan oldin tekshiring:
  ```
  python manage.py check --deploy
  ```
- `db.sqlite3` va `media/` papkasi ham `.gitignore`'da — bular haqiqiy
  mijoz ma'lumotlari va yuklangan fayllarni o'z ichiga oladi, Git'ga
  qo'shilmasligi shart.

### So'rovlar chegarasi (rate limiting)

Mijozga ochiq POST manzillari — taklifnoma yaratish, RSVP javobi va
mehmon qo'shish — IP bo'yicha cheklangan (`taklif/chegara.py`). Chegara
oshsa mijozga 429 kodi bilan "Biroz kuting" sahifasi ko'rsatiladi va
Telegram'ga ogohlantirish yuboriladi.

Hisob **bazadagi kesh jadvalida** yuritiladi, chunki u barcha gunicorn
ishchilari uchun umumiy bo'lishi shart. Jadval bir marta yaratiladi:

```
python manage.py createcachetable
```

Bu buyruq bajarilmasa, chegarani tekshirish paytida `relation "oq_kesh"
does not exist` xatosi chiqadi.

`DJANGO_BEHIND_PROXY=1` bu yerda ham muhim: usiz `CF-Connecting-IP` va
`X-Forwarded-For` sarlavhalariga **ishonilmaydi**. Sayt Cloudflare
ortida turgani uchun bu bayroqsiz barcha mijozlar bitta IP dan
kelayotgandek ko'rinadi va chegara hammani birdan to'sib qo'yadi.

## Production xizmatlari (gunicorn + nginx)

Serverda ishlab turgan haqiqiy konfiguratsiyaning nusxasi `dizayn/server/`
papkasida saqlanadi — serverni noldan tiklash yoki yangi VPS'ga ko'chirish
kerak bo'lganda shu fayllardan foydalaniladi:

- `oqqushlar-gunicorn.service` — Django ilovasini `127.0.0.1:8000`da
  ishga tushiradigan systemd xizmati (WSGI, 3 ishchi jarayon).
- `oqqushlar-nginx.conf` — teskari-proksi: statik/media fayllarni
  to'g'ridan-to'g'ri beradi, qolganini gunicorn'ga uzatadi; SSL qismi
  Certbot tomonidan avtomatik boshqariladi.
- `oqqushlar-logrotate.conf` — gunicorn jurnal faylini (`gunicorn.log`)
  haftalik aylantiradi (8 hafta saqlanadi, eskilari siqiladi) — bu
  bo'lmasa fayl cheksiz o'sadi.

O'rnatish tartibi (serverda, root sifatida):

    cp dizayn/server/oqqushlar-gunicorn.service /etc/systemd/system/oqqushlar.service
    systemctl daemon-reload
    systemctl enable --now oqqushlar.service

    cp dizayn/server/oqqushlar-nginx.conf /etc/nginx/sites-available/oqqushlar
    ln -s /etc/nginx/sites-available/oqqushlar /etc/nginx/sites-enabled/oqqushlar
    nginx -t
    systemctl reload nginx

    cp dizayn/server/oqqushlar-logrotate.conf /etc/logrotate.d/oqqushlar

Yangi serverda SSL sertifikati hali yo'q bo'lsa, avval `oqqushlar-nginx.conf`
faylining faqat `listen 80` qismi bilan (SSL qatorlarisiz) qo'yiladi, keyin
`certbot --nginx -d oqqushlar.uz -d www.oqqushlar.uz` ishga tushiriladi — u
SSL qatorlarini avtomatik qo'shib, faylni joriy ko'rinishga keltiradi.

## Zaxira nusxa

Baza har kecha 03:15 da shifrlanib R2'ning **alohida** paqiriga yuboriladi
(`taklif/management/commands/zaxira.py`). Media paqiri bilan bir joyda
saqlanmaydi: bitta noto'g'ri kalit ikkalasini birdan yo'q qilmasligi kerak.

`.env` da sozlanadi:

    ZAXIRA_BUCKET=oqqushlar-zaxira
    ZAXIRA_PAROL=<uzun tasodifiy parol, kamida 20 belgi>
    ZAXIRA_ACCESS_KEY_ID=<ixtiyoriy, alohida R2 kaliti>
    ZAXIRA_SECRET_ACCESS_KEY=<ixtiyoriy>
    ZAXIRA_ENDPOINT_URL=<ixtiyoriy>

**ZAXIRA_PAROL ni yo'qotmang.** U yo'qolsa nusxalarni ochib bo'lmaydi.
Uni parol menejeringizda, serverdan tashqarida saqlang.

Xizmat ROOT emas, alohida imtiyozsiz foydalanuvchi ostida ishlaydi —
shuning uchun taymer o'rnatishdan OLDIN, serverda BIR MARTA (root
sifatida) shu foydalanuvchi yaratiladi:

    useradd --system --no-create-home --shell /usr/sbin/nologin oqqushlar-zaxira
    setfacl -R -m u:oqqushlar-zaxira:rX /opt/oqqushlar
    setfacl -R -d -m u:oqqushlar-zaxira:rX /opt/oqqushlar

(`setfacl` topilmasa: `apt install -y acl`.) Bu foydalanuvchiga loyiha
papkasini FAQAT o'qish huquqi beriladi — yozish huquqi yo'q, chunki
zaxira buyrug'iga umuman kerak emas (natija to'g'ridan-to'g'ri R2'ga
ketadi, diskka yozilmaydi).

Taymer:

    cp dizayn/server/oqqushlar-zaxira.* /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable --now oqqushlar-zaxira.timer

Foydali buyruqlar:

    venv/bin/python manage.py zaxira --royxat    # mavjud nusxalar
    venv/bin/python manage.py zaxira --tekshir   # oxirgisi ochiladimi va o'qiladimi
    systemctl list-timers oqqushlar-zaxira       # keyingi ishga tushish vaqti
    journalctl -u oqqushlar-zaxira -n 50         # jurnal

Saqlash muddati: oxirgi 14 kun — har kungi nusxa; keyingi 8 hafta — faqat
yakshanbadagilar; undan eskisi o'chiriladi.

### Tiklash

    gpg -d oqqushlar-2026-09-09-0315.dump.gpg > tiklash.dump
    pg_restore -d <baza_nomi> --clean --if-exists tiklash.dump

Zaxira BOR bo'lishi yetarli emas — u TIKLANADIGAN bo'lishi kerak.
`--tekshir` buni qisman avtomatlashtiradi (faylni ochib, ichidagi
jadvallarni o'qib ko'radi), lekin yiliga bir marta haqiqiy tiklashni
sinov bazasida bajarib ko'rgan ma'qul.
