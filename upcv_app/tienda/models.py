import logging
from decimal import Decimal
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    descripcion = models.TextField(blank=True)
    imagen = models.ImageField(upload_to='tienda/categorias/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'categoría de producto'
        verbose_name_plural = 'categorías de productos'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.nombre)
        super().save(*args, **kwargs)


class MarcaProducto(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    logo = models.ImageField(upload_to='tienda/marcas/', blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'marca de producto'
        verbose_name_plural = 'marcas de productos'

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.nombre)
        super().save(*args, **kwargs)


class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.PROTECT, related_name='productos')
    marca = models.ForeignKey(MarcaProducto, on_delete=models.SET_NULL, related_name='productos', blank=True, null=True)
    nombre = models.CharField(max_length=220)
    slug = models.SlugField(max_length=240, unique=True, blank=True)
    descripcion_corta = models.CharField(max_length=350, blank=True)
    descripcion_larga = models.TextField(blank=True)
    codigo_sku = models.CharField(max_length=80, unique=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Precio de costo')
    precio_oferta = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text='Indique el costo de envío de este producto. Si es 0, se considerará envío gratuito para este producto.')
    imagen_principal = models.ImageField(upload_to='tienda/productos/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    nuevo = models.BooleanField(default=False)
    mostrar_en_catalogo = models.BooleanField(default=True)
    permite_compra = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [models.Index(fields=['slug']), models.Index(fields=['codigo_sku'])]

    def __str__(self):
        return f'{self.codigo_sku} - {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(self, self.nombre)
        super().save(*args, **kwargs)

    @property
    def tiene_oferta(self):
        return self.precio_oferta is not None and self.precio_oferta < self.precio

    @property
    def precio_actual(self):
        return self.precio_oferta if self.tiene_oferta else self.precio

    @property
    def en_oferta(self):
        return self.tiene_oferta

    @property
    def porcentaje_descuento(self):
        if self.tiene_oferta and self.precio:
            return round(((self.precio - self.precio_oferta) / self.precio) * 100)
        return 0

    @property
    def imagenes_activas(self):
        return self.imagenes.filter(activo=True).order_by('-principal', 'orden', 'id')

    @property
    def imagen_destacada(self):
        principal = self.imagenes.filter(activo=True, principal=True).order_by('orden', 'id').first()
        if principal:
            return principal.imagen
        primera = self.imagenes.filter(activo=True).order_by('orden', 'id').first()
        if primera:
            return primera.imagen
        return self.imagen_principal

    @property
    def agotado(self):
        return self.stock <= 0

    @property
    def disponible_para_compra(self):
        return self.activo and self.mostrar_en_catalogo and self.permite_compra and self.stock > 0

    @property
    def ganancia_unitaria(self):
        return (self.precio_actual or Decimal('0.00')) - (self.precio_costo or Decimal('0.00'))

    @property
    def margen_ganancia(self):
        if self.precio_costo and self.precio_costo > 0:
            return (self.ganancia_unitaria / self.precio_costo) * 100
        return Decimal('0.00')


class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='tienda/productos/galeria/')
    alt = models.CharField(max_length=150, blank=True, null=True)
    orden = models.PositiveIntegerField(default=0)
    principal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return self.alt or self.producto.nombre

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.principal:
            ImagenProducto.objects.filter(producto=self.producto, principal=True).exclude(pk=self.pk).update(principal=False)


class ClientePedido(models.Model):
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    direccion = models.TextField()
    departamento = models.CharField(max_length=120)
    municipio = models.CharField(max_length=120)
    nit = models.CharField(max_length=30, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'.strip()


class UbicacionTienda(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.TextField()
    departamento = models.CharField(max_length=100, blank=True, null=True)
    municipio = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    horario = models.CharField(max_length=200, blank=True, null=True)
    google_maps_url = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'ubicación de tienda'
        verbose_name_plural = 'ubicaciones de tienda'

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        RECIBIDO = 'recibido', 'Recibido'
        PAGO_EN_REVISION = 'pago_en_revision', 'Pago en revisión'
        PAGO_CONFIRMADO = 'pago_confirmado', 'Pago confirmado'
        PREPARANDO = 'preparando', 'Preparando'
        ENVIADO = 'enviado', 'Enviado'
        ENTREGADO = 'entregado', 'Entregado'
        LISTO_RECOGER = 'listo_recoger', 'Listo para recoger en tienda'
        CANCELADO = 'cancelado', 'Cancelado'
        RECHAZADO = 'rechazado', 'Rechazado'

    class EstadoPago(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        COMPROBANTE_RECIBIDO = 'comprobante_recibido', 'Comprobante recibido'
        CONFIRMADO = 'confirmado', 'Confirmado'
        RECHAZADO = 'rechazado', 'Rechazado'

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = 'transferencia_bancaria', 'Transferencia bancaria'

    class TipoEntrega(models.TextChoices):
        RECOGER_TIENDA = 'recoger_tienda', 'Recoger en tienda'
        ENVIO_DOMICILIO = 'envio_domicilio', 'Envío a domicilio'

    codigo_pedido = models.CharField(max_length=30, unique=True, blank=True)
    cliente = models.ForeignKey(ClientePedido, on_delete=models.PROTECT, related_name='pedidos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='pedidos_tienda', blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_envio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    tipo_entrega = models.CharField(max_length=30, choices=TipoEntrega.choices, default=TipoEntrega.ENVIO_DOMICILIO)
    ubicacion_recogida = models.ForeignKey(UbicacionTienda, on_delete=models.SET_NULL, blank=True, null=True, related_name='pedidos')
    direccion_entrega = models.TextField(blank=True, null=True)
    departamento_entrega = models.CharField(max_length=100, blank=True, null=True)
    municipio_entrega = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo_pago = models.CharField(max_length=40, choices=MetodoPago.choices, default=MetodoPago.TRANSFERENCIA)
    estado_pago = models.CharField(max_length=30, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
    comprobante_transferencia = models.FileField(upload_to='tienda/comprobantes/', blank=True, null=True)
    banco_origen = models.CharField(max_length=120, blank=True)
    numero_referencia = models.CharField(max_length=120, blank=True)
    fecha_transferencia = models.DateField(blank=True, null=True)
    observaciones_cliente = models.TextField(blank=True)
    observaciones_admin = models.TextField(blank=True)
    correo_confirmacion_enviado = models.BooleanField(default=False)
    fecha_correo_confirmacion = models.DateTimeField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [models.Index(fields=['codigo_pedido']), models.Index(fields=['estado', 'estado_pago'])]

    def __str__(self):
        return self.codigo_pedido

    def save(self, *args, **kwargs):
        estado_anterior = None
        update_fields = kwargs.get('update_fields')
        debe_revisar_estado = update_fields is None or 'estado' in update_fields

        if self.pk and debe_revisar_estado:
            estado_anterior = Pedido.objects.filter(pk=self.pk).values_list('estado', flat=True).first()

        if not self.codigo_pedido:
            year = timezone.now().year
            last_id = (Pedido.objects.order_by('-id').values_list('id', flat=True).first() or 0) + 1
            self.codigo_pedido = f'PED-{last_id:06d}-{year}'
        super().save(*args, **kwargs)

        if estado_anterior and estado_anterior != self.estado:
            pedido_id = self.pk
            transaction.on_commit(lambda: Pedido.objects.get(pk=pedido_id).enviar_correo_cambio_estado())

    def obtener_email_cliente(self):
        cliente = getattr(self, 'cliente', None)
        if cliente:
            email = getattr(cliente, 'email', None)
            if email:
                return email
            correo = getattr(cliente, 'correo', None)
            if correo:
                return correo

        usuario = getattr(self, 'usuario', None)
        if usuario and getattr(usuario, 'email', None):
            return usuario.email

        for campo in ('email_cliente', 'correo', 'email'):
            valor = getattr(self, campo, None)
            if valor:
                return valor

        return None

    def obtener_mensaje_estado(self):
        mensajes = {
            self.Estado.PENDIENTE: 'Tu pedido ha sido recibido y está pendiente de confirmación.',
            self.Estado.RECIBIDO: 'Tu pedido fue registrado correctamente y está pendiente de revisión.',
            self.Estado.PAGO_EN_REVISION: 'Tu comprobante de pago fue recibido y está en revisión.',
            self.Estado.PAGO_CONFIRMADO: 'El pago de tu pedido fue confirmado.',
            self.Estado.PREPARANDO: 'Tu pedido está siendo preparado.',
            self.Estado.ENVIADO: 'Tu pedido ha sido enviado.',
            self.Estado.ENTREGADO: 'Tu pedido fue entregado.',
            self.Estado.LISTO_RECOGER: 'Tu pedido ya está listo para recoger en tienda.',
            self.Estado.CANCELADO: 'Tu pedido fue cancelado.',
            self.Estado.RECHAZADO: 'Tu pedido fue rechazado.',
        }
        return mensajes.get(self.estado, f'Tu pedido cambió al estado: {self.get_estado_display()}')

    def enviar_correo_cambio_estado(self):
        email_cliente = self.obtener_email_cliente()
        if not email_cliente:
            return False

        mensaje_estado = self.obtener_mensaje_estado()
        contexto = {
            'pedido': self,
            'cliente': getattr(self, 'cliente', None),
            'mensaje_estado': mensaje_estado,
        }
        asunto = f'Actualización de tu pedido {self.codigo_pedido}'
        text_content = render_to_string('tienda/emails/cambio_estado_pedido.txt', contexto)
        html_content = render_to_string('tienda/emails/cambio_estado_pedido.html', contexto)
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[email_cliente],
        )
        email.attach_alternative(html_content, 'text/html')
        try:
            email.send(fail_silently=False)
            return True
        except Exception:
            logger.exception(
                'Error enviando correo de cambio de estado del pedido %s',
                getattr(self, 'codigo_pedido', self.pk),
            )
            return False


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, related_name='detalles_pedido', blank=True, null=True)
    nombre_producto_snapshot = models.CharField(max_length=220)
    codigo_sku_snapshot = models.CharField(max_length=80)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    costo_envio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    costo_envio_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.cantidad} x {self.nombre_producto_snapshot}'

    @property
    def costo_total(self):
        return self.precio_costo_unitario * self.cantidad

    @property
    def ganancia_total(self):
        return self.subtotal - self.costo_total


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    nit = models.CharField(max_length=20, blank=True, null=True)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    ESTADOS = [('pendiente', 'Pendiente'), ('credito', 'Al crédito'), ('pagado_parcial', 'Pagado parcial'), ('pagado', 'Pagado'), ('anulado', 'Anulado')]
    ORIGENES = [('pos', 'POS'), ('tienda', 'Tienda en línea')]
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas')
    origen = models.CharField(max_length=20, choices=ORIGENES, default='pos')
    estado = models.CharField(max_length=30, choices=ESTADOS, default='pendiente')
    fecha = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    descuento_tipo = models.CharField(max_length=20, choices=[('fijo', 'Fijo'), ('porcentaje', 'Porcentaje')], default='fijo')
    descuento_valor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    envio = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_pos')
    stock_descontado = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha']
        permissions = [('acceder_pos', 'Puede acceder al POS'), ('ver_dashboard_ventas', 'Puede ver dashboard de ventas')]

    def __str__(self):
        return f'Venta #{self.pk or 0:06d}'

    @property
    def nombre_vendedor(self):
        if self.usuario:
            nombre = self.usuario.get_full_name()
            if nombre:
                return nombre
            return self.usuario.username
        return 'No registrado'

    @property
    def subtotal_productos(self):
        return sum((detalle.subtotal for detalle in self.detalles.all()), Decimal('0.00'))

    @property
    def subtotal(self):
        return self.subtotal_productos

    @property
    def descuento_monto(self):
        subtotal = self.subtotal_productos
        valor = self.descuento_valor or Decimal('0.00')
        if valor <= 0:
            return Decimal('0.00')
        if self.descuento_tipo == 'porcentaje':
            descuento = subtotal * valor / Decimal('100')
        else:
            descuento = valor
        if descuento < 0:
            return Decimal('0.00')
        return min(descuento, subtotal)

    @property
    def descuento_total(self):
        return self.descuento_monto

    @property
    def impuesto_monto(self):
        porcentaje = self.impuesto_porcentaje or Decimal('0.00')
        base = self.subtotal_productos - self.descuento_monto
        return (base * porcentaje) / Decimal('100') if porcentaje > 0 else Decimal('0.00')

    @property
    def impuesto_total(self):
        return self.impuesto_monto

    @property
    def total(self):
        return self.subtotal_productos - self.descuento_monto + self.impuesto_monto + (self.envio or Decimal('0.00'))

    @property
    def costo_total(self):
        return sum((detalle.costo_total for detalle in self.detalles.all()), Decimal('0.00'))

    @property
    def ganancia_bruta(self):
        return self.subtotal_productos - self.descuento_monto - self.costo_total

    @property
    def ganancia_cobrada(self):
        if self.total <= 0:
            return Decimal('0.00')
        porcentaje_pagado = self.total_pagado / self.total
        return self.ganancia_bruta * porcentaje_pagado

    @property
    def ganancia_total(self):
        return self.ganancia_bruta

    @property
    def tiene_detalles_sin_costo(self):
        return any(detalle.precio_costo_unitario <= 0 for detalle in self.detalles.all())

    @property
    def total_pagado(self):
        return sum((pago.monto for pago in self.pagos.all()), Decimal('0.00'))

    @property
    def saldo_pendiente(self):
        saldo = self.total - self.total_pagado
        return saldo if saldo > 0 else Decimal('0.00')

    def actualizar_estado_pago(self, commit=True):
        if self.estado == 'anulado':
            return self.estado
        total_pagado = self.total_pagado
        total = self.total
        if total_pagado >= total and total > 0:
            self.estado = 'pagado'
        elif total_pagado > 0:
            self.estado = 'pagado_parcial'
        else:
            self.estado = 'credito' if total > 0 else 'pendiente'
        if commit:
            self.save(update_fields=['estado'])
        return self.estado


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_venta')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    @property
    def subtotal(self):
        return (self.precio_unitario or Decimal('0.00')) * self.cantidad

    @property
    def costo_total(self):
        return (self.precio_costo_unitario or Decimal('0.00')) * self.cantidad

    @property
    def ganancia_total(self):
        return self.subtotal - self.costo_total


class CotizacionPOS(models.Model):
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aprobada', 'Aprobada'),
        ('convertida', 'Convertida en venta'),
        ('vencida', 'Vencida'),
        ('anulada', 'Anulada'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_pos')
    estado = models.CharField(max_length=30, choices=ESTADOS, default='borrador')
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_pos')
    descuento_tipo = models.CharField(max_length=20, choices=[('fijo', 'Fijo'), ('porcentaje', 'Porcentaje')], default='fijo')
    descuento_valor = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    envio = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    observaciones = models.TextField(blank=True, null=True)
    venta_convertida = models.OneToOneField(Venta, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizacion_origen')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'cotización POS'
        verbose_name_plural = 'cotizaciones POS'

    def __str__(self):
        return f'Cotización #{self.pk or 0:06d}'

    @property
    def nombre_vendedor(self):
        if self.usuario:
            nombre = self.usuario.get_full_name()
            if nombre:
                return nombre
            return self.usuario.username
        return 'No registrado'

    @property
    def subtotal_productos(self):
        return sum((detalle.subtotal for detalle in self.detalles.all()), Decimal('0.00'))

    @property
    def descuento_monto(self):
        subtotal = self.subtotal_productos
        valor = self.descuento_valor or Decimal('0.00')
        if self.descuento_tipo == 'porcentaje':
            descuento = subtotal * valor / Decimal('100')
        else:
            descuento = valor
        if descuento < 0:
            return Decimal('0.00')
        return min(descuento, subtotal)

    @property
    def impuesto_monto(self):
        base = self.subtotal_productos - self.descuento_monto
        porcentaje = self.impuesto_porcentaje or Decimal('0.00')
        return base * porcentaje / Decimal('100')

    @property
    def total(self):
        return self.subtotal_productos - self.descuento_monto + self.impuesto_monto + (self.envio or Decimal('0.00'))


class DetalleCotizacionPOS(models.Model):
    cotizacion = models.ForeignKey(CotizacionPOS, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_cotizacion_pos')
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    precio_costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['id']

    @property
    def subtotal(self):
        return (self.precio_unitario or Decimal('0.00')) * self.cantidad

    @property
    def costo_total(self):
        return (self.precio_costo_unitario or Decimal('0.00')) * self.cantidad

    @property
    def ganancia_total(self):
        return self.subtotal - self.costo_total


class PagoVenta(models.Model):
    METODOS_PAGO = [('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'), ('tarjeta', 'Tarjeta'), ('deposito', 'Depósito'), ('otro', 'Otro')]
    venta = models.ForeignKey(Venta, related_name='pagos', on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=30, choices=METODOS_PAGO, default='efectivo')
    referencia = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_venta')
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Pago {self.monto} - {self.venta}'


class CuentaBancaria(models.Model):
    banco = models.CharField(max_length=140)
    nombre_cuenta = models.CharField(max_length=180)
    numero_cuenta = models.CharField(max_length=80)
    tipo_cuenta = models.CharField(max_length=80)
    moneda = models.CharField(max_length=20, default='GTQ')
    instrucciones = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'banco']
        verbose_name_plural = 'cuentas bancarias'

    def __str__(self):
        return f'{self.banco} - {self.numero_cuenta}'


def _unique_slug(instance, value):
    base = slugify(value)[:160] or 'item'
    slug = base
    model = instance.__class__
    counter = 2
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug
