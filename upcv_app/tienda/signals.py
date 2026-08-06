from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PagoVenta


@receiver([post_save, post_delete], sender=PagoVenta)
def sincronizar_estado_venta_por_pago(sender, instance, **kwargs):
    """Mantiene el estado persistido consistente incluso desde Django admin."""
    instance.venta.actualizar_estado_por_pagos()
