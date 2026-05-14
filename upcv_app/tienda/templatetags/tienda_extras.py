from urllib.parse import quote

from django import template
from django.urls import reverse

register = template.Library()

WHATSAPP_PRODUCTOS = '50242167103'


@register.simple_tag(takes_context=True)
def whatsapp_producto_url(context, producto):
    request = context.get('request')
    precio = getattr(producto, 'precio_actual', None) or getattr(producto, 'precio', '')
    sku = getattr(producto, 'codigo_sku', '') or 'N/A'
    url_producto = ''

    if request:
        try:
            path = reverse('tienda:detalle_producto', kwargs={'slug': producto.slug})
        except Exception:
            path = getattr(request, 'path', '')
        try:
            url_producto = request.build_absolute_uri(path)
        except Exception:
            url_producto = path

    mensaje = (
        'Hola, quiero hacer un pedido por WhatsApp.\n\n'
        f'Producto: {producto.nombre}\n'
        f'Código/SKU: {sku}\n'
        f'Precio: Q{precio}\n'
        f'Enlace: {url_producto}\n\n'
        '¿Me puede brindar más información para realizar la compra?'
    )
    return f'https://wa.me/{WHATSAPP_PRODUCTOS}?text={quote(mensaje)}'


@register.filter
def pedido_badge_class(estado):
    clases = {
        'pendiente': 'badge-warning',
        'recibido': 'badge-info',
        'pago_en_revision': 'badge-info',
        'pago_confirmado': 'badge-success',
        'preparando': 'badge-primary',
        'enviado': 'badge-primary',
        'entregado': 'badge-success',
        'cancelado': 'badge-danger',
        'rechazado': 'badge-danger',
    }
    return clases.get(estado, 'badge-secondary')


@register.filter
def pago_badge_class(estado_pago):
    clases = {
        'pendiente': 'badge-warning',
        'comprobante_recibido': 'badge-info',
        'confirmado': 'badge-success',
        'rechazado': 'badge-danger',
    }
    return clases.get(estado_pago, 'badge-secondary')


@register.filter
def comprobante_es_imagen(archivo):
    if not archivo:
        return False
    nombre = getattr(archivo, 'name', '').lower()
    return nombre.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif'))
