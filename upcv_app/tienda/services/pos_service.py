from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from tienda.models import DetalleVenta, PagoVenta, Producto, Venta


def _decimal(value, default='0.00'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError('Ingrese un monto válido.')


def _validar_ajustes(*, subtotal, descuento_tipo, descuento_valor, impuesto_porcentaje, envio):
    if descuento_tipo not in ('fijo', 'porcentaje'):
        raise ValidationError('Tipo de descuento inválido.')
    if descuento_valor < 0 or impuesto_porcentaje < 0 or envio < 0:
        raise ValidationError('Descuento, impuesto y envío no pueden ser negativos.')
    descuento = (subtotal * descuento_valor / Decimal('100')) if descuento_tipo == 'porcentaje' else descuento_valor
    if descuento > subtotal:
        raise ValidationError('El descuento no puede ser mayor al subtotal.')


def crear_venta_pos(*, usuario, cliente=None, items=None, monto_pagado=Decimal('0.00'), metodo_pago='efectivo', referencia='', observaciones='', descuento_tipo='fijo', descuento_valor=Decimal('0.00'), impuesto_porcentaje=Decimal('0.00'), envio=Decimal('0.00')):
    items = items or []
    if not items:
        raise ValidationError('Agregue al menos un producto a la venta.')
    descuento_valor = _decimal(descuento_valor)
    impuesto_porcentaje = _decimal(impuesto_porcentaje)
    envio = _decimal(envio)
    monto_pagado = _decimal(monto_pagado)
    if monto_pagado < 0:
        raise ValidationError('El pago no puede ser negativo.')

    with transaction.atomic():
        venta = Venta.objects.create(
            cliente=cliente,
            usuario=usuario,
            origen='pos',
            observaciones=observaciones,
            descuento_tipo=descuento_tipo,
            descuento_valor=descuento_valor,
            impuesto_porcentaje=impuesto_porcentaje,
            envio=envio,
        )
        subtotal = Decimal('0.00')
        for item in items:
            producto = Producto.objects.select_for_update().get(pk=item['producto_id'])
            cantidad = int(item['cantidad'])
            if cantidad <= 0:
                raise ValidationError('La cantidad debe ser mayor que cero.')
            if producto.stock < cantidad:
                raise ValidationError(f'Stock insuficiente para {producto.nombre}. Disponible: {producto.stock} unidades.')
            precio = producto.precio_actual
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio,
                precio_costo_unitario=producto.precio_costo or Decimal('0.00'),
            )
            producto.stock -= cantidad
            producto.save(update_fields=['stock', 'fecha_actualizacion'])
            subtotal += precio * cantidad

        _validar_ajustes(subtotal=subtotal, descuento_tipo=descuento_tipo, descuento_valor=descuento_valor, impuesto_porcentaje=impuesto_porcentaje, envio=envio)
        total = venta.total
        if monto_pagado > total:
            raise ValidationError('El pago no puede ser mayor al total de la venta.')
        if monto_pagado > 0:
            PagoVenta.objects.create(venta=venta, monto=monto_pagado, metodo_pago=metodo_pago, referencia=referencia, usuario=usuario, observaciones=observaciones)
        venta.actualizar_estado_pago()
        return venta


def agregar_pago_venta(*, venta, usuario, monto, metodo_pago='efectivo', referencia='', observaciones=''):
    if venta.estado == 'anulado':
        raise ValidationError('No se pueden agregar pagos a ventas anuladas.')
    monto = _decimal(monto)
    if monto <= 0:
        raise ValidationError('El pago debe ser mayor que cero.')
    if monto > venta.saldo_pendiente:
        raise ValidationError('El pago no puede ser mayor al saldo pendiente.')
    with transaction.atomic():
        pago = PagoVenta.objects.create(venta=venta, monto=monto, metodo_pago=metodo_pago, referencia=referencia, usuario=usuario, observaciones=observaciones)
        venta.actualizar_estado_pago()
        return pago


def anular_venta(venta):
    if venta.estado == 'anulado':
        return venta
    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(pk=venta.pk)
        if venta.stock_descontado:
            for detalle in venta.detalles.select_related('producto'):
                producto = Producto.objects.select_for_update().get(pk=detalle.producto_id)
                producto.stock += detalle.cantidad
                producto.save(update_fields=['stock', 'fecha_actualizacion'])
            venta.stock_descontado = False
        venta.estado = 'anulado'
        venta.save(update_fields=['estado', 'stock_descontado'])
        return venta
