from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


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
    precio_oferta = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    stock = models.PositiveIntegerField(default=0)
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
    def precio_actual(self):
        return self.precio_oferta if self.precio_oferta is not None else self.precio

    @property
    def en_oferta(self):
        return self.precio_oferta is not None and self.precio_oferta < self.precio

    @property
    def agotado(self):
        return self.stock <= 0

    @property
    def disponible_para_compra(self):
        return self.activo and self.mostrar_en_catalogo and self.permite_compra and self.stock > 0


class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='tienda/productos/galeria/')
    alt = models.CharField(max_length=180, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']

    def __str__(self):
        return self.alt or self.producto.nombre


class ClientePedido(models.Model):
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    telefono = models.CharField(max_length=30)
    email = models.EmailField()
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


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        RECIBIDO = 'recibido', 'Recibido'
        PAGO_EN_REVISION = 'pago_en_revision', 'Pago en revisión'
        PAGO_CONFIRMADO = 'pago_confirmado', 'Pago confirmado'
        PREPARANDO = 'preparando', 'Preparando'
        ENVIADO = 'enviado', 'Enviado'
        ENTREGADO = 'entregado', 'Entregado'
        CANCELADO = 'cancelado', 'Cancelado'
        RECHAZADO = 'rechazado', 'Rechazado'

    class EstadoPago(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        COMPROBANTE_RECIBIDO = 'comprobante_recibido', 'Comprobante recibido'
        CONFIRMADO = 'confirmado', 'Confirmado'
        RECHAZADO = 'rechazado', 'Rechazado'

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = 'transferencia_bancaria', 'Transferencia bancaria'

    codigo_pedido = models.CharField(max_length=30, unique=True, blank=True)
    cliente = models.ForeignKey(ClientePedido, on_delete=models.PROTECT, related_name='pedidos')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='pedidos_tienda', blank=True, null=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_envio = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.PENDIENTE)
    metodo_pago = models.CharField(max_length=40, choices=MetodoPago.choices, default=MetodoPago.TRANSFERENCIA)
    estado_pago = models.CharField(max_length=30, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
    comprobante_transferencia = models.FileField(upload_to='tienda/comprobantes/', blank=True, null=True)
    banco_origen = models.CharField(max_length=120, blank=True)
    numero_referencia = models.CharField(max_length=120, blank=True)
    fecha_transferencia = models.DateField(blank=True, null=True)
    observaciones_cliente = models.TextField(blank=True)
    observaciones_admin = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']
        indexes = [models.Index(fields=['codigo_pedido']), models.Index(fields=['estado', 'estado_pago'])]

    def __str__(self):
        return self.codigo_pedido

    def save(self, *args, **kwargs):
        if not self.codigo_pedido:
            year = timezone.now().year
            last_id = (Pedido.objects.order_by('-id').values_list('id', flat=True).first() or 0) + 1
            self.codigo_pedido = f'PED-{last_id:06d}-{year}'
        super().save(*args, **kwargs)


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, related_name='detalles_pedido', blank=True, null=True)
    nombre_producto_snapshot = models.CharField(max_length=220)
    codigo_sku_snapshot = models.CharField(max_length=80)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.cantidad} x {self.nombre_producto_snapshot}'


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
