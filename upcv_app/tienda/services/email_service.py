import logging
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from tienda.models import CuentaBancaria, Pedido

logger = logging.getLogger(__name__)


def _url_absoluta(path, request=None):
    if request is not None:
        try:
            return request.build_absolute_uri(path)
        except Exception:
            logger.exception('No se pudo construir URL absoluta para %s usando request.', path)
    site_url = getattr(settings, 'SITE_URL', '') or ''
    return urljoin(site_url.rstrip('/') + '/', path.lstrip('/')) if site_url else path


def enviar_correo_confirmacion_pedido_por_id(pedido_id, request=None):
    pedido = Pedido.objects.select_related('cliente', 'ubicacion_recogida').prefetch_related('detalles__producto').get(pk=pedido_id)
    return enviar_correo_confirmacion_pedido(pedido, request=request)


def enviar_correo_confirmacion_pedido(pedido, request=None):
    cliente = getattr(pedido, 'cliente', None)
    if not cliente or not cliente.email:
        return False

    if getattr(pedido, 'correo_confirmacion_enviado', False):
        return True

    try:
        rastreo_url = _url_absoluta(reverse('tienda:consultar_pedido'), request=request)
        pago_url = _url_absoluta(reverse('tienda:pago_transferencia', args=[pedido.codigo_pedido]), request=request)
        context = {
            'pedido': pedido,
            'cliente': cliente,
            'detalles': pedido.detalles.all(),
            'cuentas_bancarias': CuentaBancaria.objects.filter(activo=True).order_by('orden', 'banco'),
            'site_name': 'E-Shop El Progreso',
            'site_url': getattr(settings, 'SITE_URL', ''),
            'rastreo_url': rastreo_url,
            'pago_url': pago_url,
        }
        subject = f'Confirmación de pedido {pedido.codigo_pedido}'
        text_body = render_to_string('tienda/emails/pedido_confirmacion.txt', context)
        html_body = render_to_string('tienda/emails/pedido_confirmacion.html', context)
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[cliente.email],
        )
        email.attach_alternative(html_body, 'text/html')
        email.send(fail_silently=False)
        Pedido.objects.filter(pk=pedido.pk).update(
            correo_confirmacion_enviado=True,
            fecha_correo_confirmacion=timezone.now(),
        )
        return True
    except Exception:
        logger.exception('Error enviando correo de confirmación del pedido %s', getattr(pedido, 'codigo_pedido', pedido.pk))
        return False


def programar_correo_confirmacion_pedido(pedido, request=None):
    if not getattr(pedido.cliente, 'email', ''):
        return
    pedido_id = pedido.pk
    transaction.on_commit(lambda: enviar_correo_confirmacion_pedido_por_id(pedido_id, request=request))
