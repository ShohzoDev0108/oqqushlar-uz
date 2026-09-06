# Qorong'i fonli brend to'plami — Telegram va Instagram

Hamma fayl bitta manbadan (`taklif/static/taklif/gerb.svg`) va bitta
palitradan quriladi:

| | |
|---|---|
| Fon | `#14100c` (chuqur iliq qora + markazda juda yumshoq oltin nur) |
| Logotip va asosiy matn | `#f7f1e6` (saytdagi krem rang) |
| Oltin chiziq va izoh | `#c9a227` |
| Shriftlar | Cormorant Garamond (brend nomi), Manrope (izoh) |

---

## Avatarlar

Telegram ham, Instagram ham avatarni **doira** qilib kesadi, shuning
uchun ikkala faylda ham burchaklarda hech narsa yo'q.

| Fayl | Qayerga |
|---|---|
| `telegram-avatar-512.png` | Telegram kanal/bot avatari |
| `instagram-avatar-1080.png` | Instagram profil rasmi |
| `telegram-avatar-gerb-512.png` | to'liq gerbli variant |
| `instagram-avatar-gerb-1080.png` | to'liq gerbli variant |

**Qaysi birini qo'yish kerak — soddasini.** Sabab o'lchov bilan
tekshirilgan: suhbatlar ro'yxatida avatar 44–64 piksel bo'lib chiqadi.
O'sha o'lchamda to'liq gerbning ingichka naqshlari qo'shilib ketib, kul
rang dog'ga aylanadi. Soddalashtirilgan belgi (ikki oqqush bo'yni yurak
hosil qiladi) esa 44 pikselda ham aniq o'qiladi.

To'liq gerbli variantni profil sahifasining o'zida yoki katta joyda
ishlatish mumkin.

## Postlar

| Fayl | Qayerga |
|---|---|
| `instagram-post-1080x1080.png` | Instagram post, kvadrat |
| `instagram-post-1080x1350.png` | Instagram post, 4:5 — lentada eng ko'p joy egallaydi |
| `instagram-story-1080x1920.png` | Story va Reels muqovasi |
| `telegram-post-1280x720.png` | Telegram post rasmi, havola ko'rinishi (link preview) |

Story faylida ataylab **ramka yo'q** va pastda bo'sh joy qoldirilgan:
kadrning pastki ~250 pikselini Instagram o'z tugmalari bilan qoplaydi,
qolgan joyga esa matn yoki stiker qo'yish qulay.

## Qo'shimcha

`logo-oq-shaffof-2048.png` — fonsiz oq logotip. O'z rasmingiz (masalan
to'y fotosurati) ustiga qo'yish uchun. Faqat **qorong'i yoki to'q rangli**
rasm ustiga qo'ying — och fonda u ko'rinmaydi, u yerda saytdagi oddiy
oltin logotip ishlatiladi.

## Qayta yasash

`brend_yasa.py` — shu to'plamni yasagan skript. Rangni, yozuvni yoki
o'lchamni o'zgartirish kerak bo'lsa, fayl boshidagi o'zgaruvchilarni
tahrirlab, qaytadan ishga tushiring:

```
python brend_yasa.py
```

Kerak bo'ladigan kutubxonalar: `cairosvg`, `pillow`. Shriftlar skriptda
`/tmp/` dan olinadi — boshqa kompyuterda ishga tushirsangiz, `SERIF` va
`SANS` yo'llarini Cormorant Garamond va Manrope fayllariga
o'zgartiring (ikkalasi ham Google Fonts'da bepul).
