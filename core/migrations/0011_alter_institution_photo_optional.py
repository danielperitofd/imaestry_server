from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_add_card_radius'),
    ]

    operations = [
        migrations.AlterField(
            model_name='institution',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='institutions/', verbose_name='Foto/Logo'),
        ),
    ]
