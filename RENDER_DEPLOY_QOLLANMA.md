# Oqqushlar — Render'ga deploy qilish qo'llanmasi

Bu hujjat loyihani Render'da (PostgreSQL + rasmlar uchun Cloudflare R2 bilan) birinchi marta ishga tushirish uchun qadam-baqadam yo'riqnoma. Har bir qadamda men (Claude) yordam bera olaman — qayerda qotib qolsangiz, shu yerdagi qadam raqamini ayting.

Boshlashdan oldin: loyiha kodi tayyor (PostgreSQL va tashqi rasm-xotira qo'llab-quvvatlanadi, render.yaml fayli bor). Sizga qolgan ish — ikkita xizmatda (Cloudflare, Render) hisob ochish va ularni bir-biriga ulash.

## 0-qadam: kodni GitHub'ga yuklash

Agar hali qilmagan bo'lsangiz, avval shu tayyorgarlik o'zgarishlarini GitHub'ga yuklang (buni PowerShell'da, loyiha papkasida bajaring):

```
git add .
git commit -m "Production uchun tayyorlash: PostgreSQL, tashqi rasm-xotira, gunicorn"
git push
```

## 1-qadam: Cloudflare R2 — rasmlar uchun doimiy xotira

Bu qadam MUHIM — shusiz mijozlar yuklagan taklifnoma rasmlari deploy paytida yo'qolib qolishi mumkin.

1. https://dash.cloudflare.com ga kiring (hisobingiz yo'q bo'lsa, bepul ro'yxatdan o'ting).
2. Chap menyudan **R2 Object Storage** bo'limini toping va oching (birinchi marta bo'lsa, karta ma'lumotini so'rashi mumkin — R2'ning o'zi kichik loyihalar uchun deyarli tekin, oyiga 10GB'gacha bepul).
3. **Create bucket** tugmasini bosing. Nom bering, masalan: `oqqushlar-media`. Region — "Automatic" qoldirilsa bo'ladi.
4. Bucket yaratilgach, **Settings** bo'limiga o'ting va **Public access** ni yoqing (mijozlar rasmlarni ko'rishi uchun ochiq bo'lishi kerak) — bu yerda sizga bir ochiq URL (masalan `pub-xxxxx.r2.dev`) beriladi, uni eslab qoling (keyinroq kerak bo'lmasligi ham mumkin).
5. Chap menyudan **R2 -> Manage API Tokens** ga o'ting, **Create API Token** bosing. Ruxsat turi: "Object Read & Write". Faqat yuqorida yaratgan bucket'ga cheklab qo'ysangiz xavfsizroq.
6. Token yaratilgach sizga 3 ta qiymat ko'rsatiladi — **buni faqat shu paytda ko'rasiz, keyin qayta ko'rinmaydi**, albatta nusxalab saqlang:
   - `Access Key ID`
   - `Secret Access Key`
   - `Endpoint` manzili (masalan `https://<hisob-ID>.r2.cloudflarestorage.com`)

Shu 3 ta qiymat + bucket nomi (`oqqushlar-media`) — Render'da kerak bo'ladi.

## 2-qadam: Render'da hisob ochish

1. https://render.com ga kiring, GitHub hisobingiz orqali ro'yxatdan o'ting (shunda GitHub repo'laringizni bevosita ko'radi).

## 3-qadam: Blueprint orqali serverni yaratish

Loyihada tayyor `render.yaml` fayli bor — bu Render'ga veb-server va ma'lumotlar bazasini BIRGA, avtomatik yaratishni aytadi.

1. Render dashboard'da **New +** -> **Blueprint** ni bosing.
2. GitHub repo'ingizni (oqqushlar-uz) tanlang va ulashga ruxsat bering.
3. Render `render.yaml` faylini o'zi topib, nima yaratmoqchi ekanini ko'rsatadi (1 ta veb-server + 1 ta PostgreSQL baza). **Apply** bosing.
4. Render sizdan `sync: false` deb belgilangan o'zgaruvchilarni so'raydi — shu yerda quyidagilarni kiritasiz:

   | O'zgaruvchi | Nima yozish kerak |
   |---|---|
   | `DJANGO_ALLOWED_HOSTS` | Avval Render bergan vaqtinchalik domen, masalan `oqqushlar.onrender.com` (keyinroq o'z domeningizni qo'shasiz) |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://oqqushlar.onrender.com` |
   | `AWS_ACCESS_KEY_ID` | 1-qadamda olgan Access Key ID |
   | `AWS_SECRET_ACCESS_KEY` | 1-qadamda olgan Secret Access Key |
   | `AWS_STORAGE_BUCKET_NAME` | `oqqushlar-media` |
   | `AWS_S3_ENDPOINT_URL` | 1-qadamda olgan Endpoint manzili |
   | `AWS_S3_CUSTOM_DOMAIN` | Hozircha bo'sh qoldiring |
   | `SAYT_ADMIN_TELEGRAM` | Sizning Telegram username'ingiz |
   | `GOOGLE_ANALYTICS_ID` | Agar bor bo'lsa GA4 ID'ingiz, yo'q bo'lsa bo'sh |

   `DJANGO_SECRET_KEY` va `DATABASE_URL` — bularni Render **o'zi avtomatik** to'ldiradi, hech narsa yozish shart emas.

5. Tasdiqlagach, Render avtomatik: kodni yuklab oladi, kerakli paketlarni o'rnatadi, statik fayllarni yig'adi, ma'lumotlar bazasi jadvallarini yaratadi (migratsiya) va serverni ishga tushiradi. Bu bir necha daqiqa vaqt oladi — "Logs" bo'limidan jarayonni jonli kuzatishingiz mumkin.

## 4-qadam: tekshirish

1. Deploy tugagach, Render bergan vaqtinchalik manzilni (masalan `https://oqqushlar.onrender.com`) brauzerda oching — sayt ochilishi kerak.
2. `/admin/` sahifasiga kirib ko'ring. Birinchi admin foydalanuvchi hali yo'q — buni Render dashboard'dagi "Shell" bo'limidan (veb-servisingizni oching -> yuqoridagi "Shell" tab) shu buyruq bilan yaratasiz:
   ```
   python manage.py createsuperuser
   ```
3. Bir nechta shablon sahifasini ochib, rasm/dizayn to'g'ri chiqayotganini tekshiring.

## 5-qadam: o'z domeningizni ulash (taklifnoma365.uz)

1. Render'da veb-servisingiz sozlamalarida **Custom Domains** bo'limiga o'ting, domeningizni kiriting.
2. Render sizga DNS yozuvi (CNAME yoki A record) beradi — buni domeningizni sotib olgan joyda (masalan domain registrar boshqaruv panelida) qo'shasiz. Bu qadamda ham yordam bera olaman — domen provayderingiz nomini ayting.
3. DNS tarqalgach (odatda bir necha daqiqadan bir necha soatgacha), SSL sertifikat Render tomonidan avtomatik chiqariladi.
4. Domen ishga tushgach, `DJANGO_ALLOWED_HOSTS` va `DJANGO_CSRF_TRUSTED_ORIGINS` o'zgaruvchilariga yangi domeningizni ham qo'shib qo'ying (Render dashboard -> Environment).

## Muammo yuzaga kelsa

Render'ning "Logs" bo'limida xatolik matnini toping va menga nusxalab yuboring — birga hal qilamiz. Eng ko'p uchraydigan narsalar: `DJANGO_ALLOWED_HOSTS`da domen yozilmagan, yoki R2 kalitlaridan biri noto'g'ri kiritilgan.
