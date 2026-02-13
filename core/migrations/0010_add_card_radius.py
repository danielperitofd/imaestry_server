from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_add_extended_theme_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='themeconfig',
            name='card_radius',
            field=models.PositiveSmallIntegerField(default=12, verbose_name='Raio dos Cards (px)'),
        ),
    ]
