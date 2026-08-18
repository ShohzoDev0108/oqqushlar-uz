import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("taklif", "0005_mehmon_rsvp_mehmon_mehmon_taklif_mehmon_slug_unique"),
    ]

    operations = [
        # Ism maydonlarini umumiy nomga o'tkazamiz (mavjud ma'lumot saqlanadi):
        # kuyov -> ism_1, kelin -> ism_2
        migrations.RenameField(
            model_name="taklifnoma",
            old_name="kuyov",
            new_name="ism_1",
        ),
        migrations.RenameField(
            model_name="taklifnoma",
            old_name="kelin",
            new_name="ism_2",
        ),
        migrations.AlterField(
            model_name="taklifnoma",
            name="ism_1",
            field=models.CharField(
                help_text="Masalan: kelin, tug'ilgan kun egasi", max_length=100
            ),
        ),
        migrations.AlterField(
            model_name="taklifnoma",
            name="ism_2",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Ikkinchi ism (masalan: kuyov). Kerak bo'lmasa bo'sh qoldiring"
                ),
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="taklifnoma",
            name="sana",
            field=models.DateTimeField(help_text="Tadbir sanasi va vaqti"),
        ),
        migrations.AlterField(
            model_name="taklifnoma",
            name="musiqa",
            field=models.FileField(
                blank=True,
                help_text="O'zingiz yuklamoqchi bo'lsangiz",
                upload_to="musiqa/",
            ),
        ),
        migrations.AddField(
            model_name="taklifnoma",
            name="marosim_turi",
            field=models.CharField(
                choices=[
                    ("toy", "To'y"),
                    ("qizlar_bazmi", "Qizlar bazmi"),
                    ("sunnat_toy", "Sunnat to'yi"),
                    ("yubiley", "Yubiley"),
                    ("tugilgan_kun", "Tug'ilgan kun"),
                    ("boshqa", "Boshqa"),
                ],
                default="toy",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="taklifnoma",
            name="yoqdi_bosildi",
            field=models.BooleanField(
                default=False,
                editable=False,
                help_text="Mijoz 'Yoqdi' tugmasini bosganmi",
            ),
        ),
        migrations.CreateModel(
            name="MusiqaVariant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "nomi",
                    models.CharField(
                        help_text="Masalan: Lirik, Milliy, Zamonaviy", max_length=100
                    ),
                ),
                ("fayl", models.FileField(upload_to="musiqa_variantlari/")),
                ("faol", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Tayyor musiqa varianti",
                "verbose_name_plural": "Tayyor musiqa variantlari",
                "ordering": ["nomi"],
            },
        ),
        migrations.AddField(
            model_name="taklifnoma",
            name="musiqa_variant",
            field=models.ForeignKey(
                blank=True,
                help_text="Tayyor musiqalardan birini tanlash",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="taklifnomalar",
                to="taklif.musiqavariant",
            ),
        ),
    ]
