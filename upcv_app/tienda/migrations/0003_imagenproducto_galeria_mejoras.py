import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('tienda', '0002_create_store_groups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagenproducto',
            name='alt',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name='imagenproducto',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='imagenproducto',
            name='principal',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='imagenproducto',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
