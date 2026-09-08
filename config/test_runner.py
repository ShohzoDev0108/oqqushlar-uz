# -*- coding: utf-8 -*-
"""Testlar uchun maxsus ishga tushirgich.

MUAMMO. Testlar fayl yuklashni sinaydi — rasm, musiqa. Django esa
yuklangan faylni MEDIA_ROOT ga, ya'ni loyihaning O'Z "media/" papkasiga
yozardi. Test tugagach fayl o'sha yerda qolib ketardi, va nomi band
bo'lgani uchun Django unga tasodifiy qo'shimcha qo'shardi:

    media/namuna_rasmlar/n_HRrzR4g.jpg
    media/namuna_rasmlar/n2_QRDxo2j.jpg

Har bir test ishga tushganda yana bir nechtasi qo'shilardi. Ular
"git status"da doimiy chiqib turardi va bir nechtasi tasodifan
"git add ." bilan repozitoriyga ham tushib ketgan.

YECHIM. Test paytida MEDIA_ROOT vaqtinchalik papkaga ko'chiriladi va
testlar tugagach o'sha papka butunlay o'chiriladi. Loyihaning "media/"
papkasiga endi test hech narsa yozmaydi.

NEGA settings.py'da emas. Sozlamalar fayliga "agar test bo'lsa..."
degan shart qo'shish — production sozlamasini test bilan aralashtirish
degani. Django buning uchun rasmiy joy beradi: TEST_RUNNER.
"""
import shutil
import tempfile

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class OqqushlarTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._media_papka = tempfile.mkdtemp(prefix="oqqushlar-test-media-")
        self._ozgartirish = override_settings(MEDIA_ROOT=self._media_papka)
        self._ozgartirish.enable()

    def teardown_test_environment(self, **kwargs):
        self._ozgartirish.disable()
        shutil.rmtree(self._media_papka, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
