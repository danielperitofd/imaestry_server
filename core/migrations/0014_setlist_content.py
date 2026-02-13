from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_team_announcement_likes'),
    ]

    operations = [
        migrations.AddField(
            model_name='setlist',
            name='content',
            field=models.TextField(blank=True, verbose_name='Conteúdo (JSON)'),
        ),
    ]
