from django.contrib import admin
from .models import CategoriaProducto, MarcaProducto, Producto, ImagenProducto, ClientePedido, Pedido, DetallePedido, CuentaBancaria


class ImagenProductoInline(admin.TabularInline):
    model = ImagenProducto
    extra = 1
    fields = ('imagen', 'alt', 'orden', 'principal', 'activo')


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'activo', 'orden', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(MarcaProducto)
class MarcaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)
    prepopulated_fields = {'slug': ('nombre',)}


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo_sku', 'nombre', 'categoria', 'marca', 'precio', 'precio_oferta', 'stock', 'activo', 'destacado')
    list_filter = ('activo', 'destacado', 'nuevo', 'permite_compra', 'categoria', 'marca')
    search_fields = ('nombre', 'codigo_sku', 'descripcion_corta')
    prepopulated_fields = {'slug': ('nombre',)}
    inlines = [ImagenProductoInline]


@admin.register(ImagenProducto)
class ImagenProductoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'alt', 'orden', 'principal', 'activo', 'fecha_creacion')
    list_filter = ('principal', 'activo')
    search_fields = ('producto__nombre', 'alt')


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ('producto', 'nombre_producto_snapshot', 'codigo_sku_snapshot', 'precio_unitario', 'cantidad', 'subtotal')


@admin.register(ClientePedido)
class ClientePedidoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'telefono', 'email', 'departamento', 'municipio')
    search_fields = ('nombres', 'apellidos', 'telefono', 'email', 'nit')


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('codigo_pedido', 'cliente', 'total', 'estado', 'estado_pago', 'metodo_pago', 'fecha_creacion')
    list_filter = ('estado', 'estado_pago', 'metodo_pago', 'fecha_creacion')
    search_fields = ('codigo_pedido', 'cliente__nombres', 'cliente__apellidos', 'cliente__email', 'cliente__telefono')
    readonly_fields = ('codigo_pedido', 'fecha_creacion', 'fecha_actualizacion')
    inlines = [DetallePedidoInline]


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'nombre_producto_snapshot', 'cantidad', 'precio_unitario', 'subtotal')
    search_fields = ('pedido__codigo_pedido', 'nombre_producto_snapshot', 'codigo_sku_snapshot')


@admin.register(CuentaBancaria)
class CuentaBancariaAdmin(admin.ModelAdmin):
    list_display = ('banco', 'nombre_cuenta', 'numero_cuenta', 'tipo_cuenta', 'moneda', 'activo', 'orden')
    list_filter = ('activo', 'moneda')
    search_fields = ('banco', 'nombre_cuenta', 'numero_cuenta')
