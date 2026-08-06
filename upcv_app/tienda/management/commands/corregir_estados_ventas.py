from django.core.management.base import BaseCommand

from tienda.models import Venta


class Command(BaseCommand):
    help = 'Corrige el estado guardado de las ventas según sus pagos reales.'

    def handle(self, *args, **options):
        actualizadas = 0
        ventas = Venta.objects.exclude(estado='anulado').prefetch_related('detalles', 'pagos')
        for venta in ventas.iterator(chunk_size=200):
            estado_real = venta.estado_real
            if venta.estado != estado_real:
                Venta.objects.filter(pk=venta.pk).update(estado=estado_real)
                actualizadas += 1

        self.stdout.write(self.style.SUCCESS(f'Ventas actualizadas: {actualizadas}'))
