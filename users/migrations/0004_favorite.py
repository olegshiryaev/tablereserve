# Generated by Django 5.0.6 on 2024-06-17 00:48

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0006_placetype_remove_establishment_cover_image_and_more'),
        ('users', '0003_alter_customuser_phone_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reservations.place')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_establishments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'place')},
            },
        ),
    ]
