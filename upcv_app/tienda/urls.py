from django.urls import path
from . import views

app_name = 'tienda'

urlpatterns = [
    path('', views.tienda_inicio, name='inicio'),
    path('productos/', views.catalogo_productos, name='catalogo'),
    path('producto/<slug:slug>/', views.detalle_producto, name='detalle_producto'),
    path('carrito/', views.carrito, name='carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_carrito, name='agregar_carrito'),
    path('carrito/actualizar/<int:producto_id>/', views.actualizar_carrito, name='actualizar_carrito'),
    path('carrito/eliminar/<int:producto_id>/', views.eliminar_carrito, name='eliminar_carrito'),
    path('checkout/', views.checkout, name='checkout'),
    path('pedido/<str:codigo_pedido>/pago/', views.pago_transferencia, name='pago_transferencia'),
    path('pedido/<str:codigo_pedido>/estado/', views.estado_pedido, name='estado_pedido'),
    path('consultar-pedido/', views.consultar_pedido, name='consultar_pedido'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/productos/', views.admin_productos, name='admin_productos'),
    path('admin/productos/crear/', views.admin_producto_form, name='admin_producto_crear'),
    path('admin/productos/<int:pk>/editar/', views.admin_producto_form, name='admin_producto_editar'),
    path('admin/productos/<int:pk>/detalle/', views.admin_producto_detalle, name='admin_producto_detalle'),
    path('admin/productos/<int:pk>/toggle/', views.admin_producto_toggle, name='admin_producto_toggle'),
    path('admin/productos/<int:producto_id>/imagenes/<int:imagen_id>/eliminar/', views.admin_producto_imagen_eliminar, name='admin_producto_imagen_eliminar'),
    path('admin/categorias/', views.admin_categorias, name='admin_categorias'),
    path('admin/categorias/crear/', views.admin_categoria_form, name='admin_categoria_crear'),
    path('admin/categorias/<int:pk>/editar/', views.admin_categoria_form, name='admin_categoria_editar'),
    path('admin/marcas/', views.admin_marcas, name='admin_marcas'),
    path('admin/marcas/crear/', views.admin_marca_form, name='admin_marca_crear'),
    path('admin/marcas/<int:pk>/editar/', views.admin_marca_form, name='admin_marca_editar'),
    path('admin/pedidos/', views.admin_pedidos, name='admin_pedidos'),
    path('admin/pedidos/<int:pk>/detalle/', views.admin_pedido_detalle, name='admin_pedido_detalle'),
    # Alias conservado para enlaces internos generados antes de estandarizar la ruta con /detalle/.
    path('admin/pedidos/<int:pk>/', views.admin_pedido_detalle, name='admin_pedido_detalle_simple'),
    path('admin/pagos-pendientes/', views.admin_pagos_pendientes, name='admin_pagos_pendientes'),
    path('admin/ubicaciones/', views.admin_ubicaciones_tienda, name='admin_ubicaciones_tienda'),
    path('admin/ubicaciones/crear/', views.admin_ubicacion_tienda_form, name='admin_ubicacion_tienda_crear'),
    path('admin/ubicaciones/<int:pk>/editar/', views.admin_ubicacion_tienda_form, name='admin_ubicacion_tienda_editar'),
    path('admin/cuentas-bancarias/', views.admin_cuentas, name='admin_cuentas_bancarias'),
    path('admin/cuentas-bancarias/crear/', views.admin_cuenta_form, name='admin_cuenta_bancaria_crear'),
    path('admin/cuentas-bancarias/<int:pk>/editar/', views.admin_cuenta_form, name='admin_cuenta_bancaria_editar'),
    # Alias conservados para compatibilidad con el primer scaffold de la app tienda.
    path('admin/cuentas/', views.admin_cuentas, name='admin_cuentas'),
    path('admin/cuentas/crear/', views.admin_cuenta_form, name='admin_cuenta_crear'),
    path('admin/cuentas/<int:pk>/editar/', views.admin_cuenta_form, name='admin_cuenta_editar'),
    path('admin/reportes/', views.admin_reportes, name='admin_reportes'),
]
