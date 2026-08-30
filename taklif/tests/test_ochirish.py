"""Mijozning o'zi taklifnomasini o'chirishi — audit bo'yicha qo'shilgan
"chiqindilar" (soft-delete) tizimi uchun testlar."""
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, TestCase, override_settings
from django.utils import timezone

from taklif.admin import TaklifnomaAdmin
from taklif.models import RSVP, Taklifnoma
from taklif.tests.yordamchi import shablon_yarat
from taklif.views import SESSIYA_KALITI


@override_settings(ALLOWED_HOSTS=["testserver"])
class OchirishTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()

    def _sessiyali_client(self, sluglar):
        c = Client()
        session = c.session
        session[SESSIYA_KALITI] = sluglar
        session.save()
        c.cookies["sessionid"] = session.session_key
        return c

    def test_boshqa_birov_ozganing_taklifnomasini_ochira_olmaydi(self):
        t = Taklifnoma.objects.create(
            slug="begona", ism_1="Begona", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        c = self._sessiyali_client([])  # sessiyada bu slug yo'q
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        self.assertTrue(Taklifnoma.objects.filter(pk=t.pk).exists())

    def test_tolanmagan_qoralama_darhol_butunlay_ochadi(self):
        t = Taklifnoma.objects.create(
            slug="qoralama", ism_1="Qoralama", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=False,
        )
        c = self._sessiyali_client([t.slug])
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        self.assertFalse(Taklifnoma.objects.filter(pk=t.pk).exists())

    def test_tolangan_taklifnoma_chiqindiga_otkaziladi_ochmaydi(self):
        t = Taklifnoma.objects.create(
            slug="tolangan", ism_1="Tolangan", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        RSVP.objects.create(taklifnoma=t, ism="Mehmon", keladi=True, mehmonlar_soni=2)

        c = self._sessiyali_client([t.slug])
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")

        t.refresh_from_db()
        self.assertTrue(Taklifnoma.objects.filter(pk=t.pk).exists())  # bazada qoladi
        self.assertFalse(t.faol)  # mehmonlarga ko'rinmay qoladi
        self.assertIsNotNone(t.ochirilgan_vaqt)
        self.assertTrue(RSVP.objects.filter(taklifnoma=t).exists())  # RSVP saqlanadi

    def test_tolangan_ochirilgach_bosh_sahifada_korinmaydi(self):
        t = Taklifnoma.objects.create(
            slug="royxatdan-yoqolishi-kerak", ism_1="Yoqoladi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        c = self._sessiyali_client([t.slug])
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        # DIQQAT: o'chirgan mijozning o'z sessiyasida "o'chirildi" degan flash
        # xabar bir martalik ko'rsatiladi (ism ham o'sha xabarda chiqadi) —
        # shuning uchun bosh sahifani BOSHQA (sessiyasiz) mijoz ko'zi bilan
        # tekshiramiz, aks holda flash xabar yolg'on-musbat (false positive)
        # beradi.
        r = Client().get("/")
        self.assertNotContains(r, "Yoqoladi")

    def test_tolangan_ochirilgach_mehmon_yopilgan_sahifani_koradi(self):
        t = Taklifnoma.objects.create(
            slug="mehmon-uchun-yopiladi", ism_1="Yopiladi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=True,
        )
        c = self._sessiyali_client([t.slug])
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        r = c.get(f"/{t.slug}/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "yopilgan")

    def test_ochirilgach_sessiyadan_ham_olib_tashlanadi(self):
        t = Taklifnoma.objects.create(
            slug="sessiyadan-olinadi", ism_1="Olinadi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=False,
        )
        c = self._sessiyali_client([t.slug])
        c.post(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        self.assertNotIn(t.slug, c.session.get(SESSIYA_KALITI, []))

    def test_get_sorovi_rad_etiladi(self):
        t = Taklifnoma.objects.create(
            slug="get-sinovi", ism_1="GetSinovi", shablon=self.shablon,
            sana=timezone.now(), faol=True, tolangan=False,
        )
        c = self._sessiyali_client([t.slug])
        r = c.get(f"/mening-taklifnomalarim/{t.slug}/ochirish/")
        self.assertEqual(r.status_code, 405)
        self.assertTrue(Taklifnoma.objects.filter(pk=t.pk).exists())


class AdminTiklashTest(TestCase):
    def setUp(self):
        self.shablon = shablon_yarat()

    def test_chiqindidan_tiklash_action(self):
        t = Taklifnoma.objects.create(
            slug="tiklanadi", ism_1="Tiklanadi", shablon=self.shablon,
            sana=timezone.now(), faol=False, tolangan=True,
            ochirilgan_vaqt=timezone.now(),
        )
        admin_obj = TaklifnomaAdmin(Taklifnoma, AdminSite())
        request = RequestFactory().get("/admin/")
        request.session = {}
        request._messages = FallbackStorage(request)

        admin_obj.chiqindidan_tiklash(request, Taklifnoma.objects.filter(pk=t.pk))

        t.refresh_from_db()
        self.assertTrue(t.faol)
        self.assertIsNone(t.ochirilgan_vaqt)
