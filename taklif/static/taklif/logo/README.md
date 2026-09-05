# Oqqushlar — brend belgisi

Hamma fayl bitta manbadan yaratilgan: `../favicon.svg` (ikkita oqqush,
yurak shaklida, sof vektor, bitta rangda). Qayta yaratish:

    python3 scratchpad/logo_toplam.py

## Qaysi birini qachon ishlatish

### Kenglikdagi belgi — sarlavha, blank, hujjat, sayt

| Fayl | Qachon |
|---|---|
| `belgi-tilla.svg` | Yorug' fonda (krem, oq) — asosiy holat |
| `belgi-oq.svg` | To'q fonda (to'q ko'k, to'q qizil, qora) |
| `belgi-qora.svg` | Bir rangli bosma: muhr, blank, faks, kashta |

### Kvadrat — avatar, favicon, ijtimoiy tarmoq

| Fayl | Qachon |
|---|---|
| `avatar-krem.svg` / `-512.png` | Telegram, Instagram — asosiy avatar |
| `avatar-toq.svg` / `-512.png` | To'q mavzudagi ilova yoki kanal |
| `avatar-pushti.svg` / `-512.png` | Mavsumiy yoki reklama kampaniyasi uchun |
| `kvadrat-tilla.svg` | Fonsiz — o'z foningizga qo'yish uchun |
| `kvadrat-oq.svg` | Fonsiz, to'q fonga |

PNG variantlari 512x512 — Telegram va Instagram SVG qabul qilmaydi.

## Nega kvadrat alohida

Belgining nisbati ~1.77:1, ya'ni u KENG. Avatar va favicon esa kvadrat.
Keng belgini to'g'ridan-to'g'ri kvadratga qo'yilsa, doira shaklida
kesilganda qanot uchlari yo'qoladi, tepa va pastda esa katta bo'sh joy
qoladi. Kvadrat variantlarda belgi ataylab kichraytirilib (kvadrat
kengligining 72% i) markazga qo'yilgan — doira ichida ham to'liq
ko'rinadi. Hisob: nisbati 1.77 bo'lgan shaklning diagonali kengligidan
1.148 marta katta, ya'ni doiraga sig'ishi uchun kenglik diametrning
87% idan oshmasligi kerak; 72% — optik zaxira bilan.

## Tegmang

`../favicon.svg` va `../gerb.svg` — manba fayllar.

* `favicon.svg` — soddalashtirilgan belgi, kichik o'lchamlar uchun.
* `gerb.svg` — naqshinkor to'liq gerb (ravoq ichida oqqushlar), FAQAT
  katta o'lchamda: bosh sahifa sarlavhasi, katta bosma. Kichraytirilsa
  naqsh loyqalanadi.

Fonsiz eski rasterlar (`logo-manba.png`, `logo-ijtimoiy-*.png/jpg`)
loyihada hech qayerda ishlatilmaydi — ular AI bilan yaratilgan dastlabki
variantlar. O'chirish mumkin, lekin zarar ham qilmaydi.
