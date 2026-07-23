from django.core.management.base import BaseCommand
from django.db import transaction

from tienda.models import DetalleVenta


class Command(BaseCommand):
    help = 'Actualiza detalles de ventas con costo histórico en cero usando el costo actual del producto.'

    def handle(self, *args, **options):
        detalles = DetalleVenta.objects.select_related('producto').filter(precio_costo_unitario=0)
        revisados = detalles.count()
        actualizados = 0
        with transaction.atomic():
            for detalle in detalles:
                producto = detalle.producto
                if producto and producto.precio_costo and producto.precio_costo > 0:
                    detalle.precio_costo_unitario = producto.precio_costo
                    detalle.save(update_fields=['precio_costo_unitario'])
                    actualizados += 1
        self.stdout.write(self.style.SUCCESS(f'Detalles revisados: {revisados}. Detalles actualizados: {actualizados}.'))
