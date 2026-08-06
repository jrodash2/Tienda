from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('tienda', '0009_cotizacionpos_detallecotizacionpos')]

    operations = [
        migrations.AlterField(
            model_name='venta',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('credito', 'Al crédito'),
                    ('pagado_parcial', 'Pagado parcial'),
                    ('pagado', 'Pagado'),
                    ('anulado', 'Anulado'),
                ],
                default='pendiente',
                max_length=30,
            ),
        ),
    ]
