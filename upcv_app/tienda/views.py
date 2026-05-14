from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from almacen_app.utils import grupo_requerido
from .cart import add_to_cart as session_add, cart_items, clear_cart, remove_from_cart as session_remove, update_cart as session_update
from .forms import (
    CambiarEstadoPedidoForm, CategoriaProductoForm, CheckoutForm, ComprobanteTransferenciaForm,
    CuentaBancariaForm, MarcaProductoForm, ProductoForm, RechazarPagoForm,
)
from .models import CategoriaProducto, ClientePedido, CuentaBancaria, DetallePedido, MarcaProducto, Pedido, Producto

ENVIO_DEFAULT = Decimal('0.00')


def tienda_inicio(request):
    productos = Producto.objects.filter(activo=True, mostrar_en_catalogo=True).select_related('categoria', 'marca')
    return render(request, 'tienda/public/inicio.html', {
        'categorias': CategoriaProducto.objects.filter(activo=True)[:8],
        'destacados': productos.filter(destacado=True)[:8],
        'nuevos': productos.filter(nuevo=True)[:8],
        'ofertas': productos.filter(precio_oferta__isnull=False)[:8],
    })


def catalogo_productos(request):
    productos = Producto.objects.filter(activo=True, mostrar_en_catalogo=True).select_related('categoria', 'marca')
    q = request.GET.get('q', '').strip()
    categoria = request.GET.get('categoria')
    marca = request.GET.get('marca')
    precio_min = request.GET.get('precio_min')
    precio_max = request.GET.get('precio_max')
    orden = request.GET.get('orden', 'recientes')
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(descripcion_corta__icontains=q) | Q(descripcion_larga__icontains=q) | Q(codigo_sku__icontains=q))
    if categoria:
        productos = productos.filter(categoria__slug=categoria)
    if marca:
        productos = productos.filter(marca__slug=marca)
    if precio_min:
        productos = productos.filter(precio__gte=precio_min)
    if precio_max:
        productos = productos.filter(precio__lte=precio_max)
    order_map = {'precio_menor': 'precio', 'precio_mayor': '-precio', 'destacados': '-destacado', 'recientes': '-fecha_creacion'}
    productos = productos.order_by(order_map.get(orden, '-fecha_creacion'))
    paginator = Paginator(productos, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'tienda/public/catalogo.html', {
        'productos': page_obj.object_list,
        'page_obj': page_obj,
        'categorias': CategoriaProducto.objects.filter(activo=True),
        'marcas': MarcaProducto.objects.filter(activo=True),
    })


def detalle_producto(request, slug):
    producto = get_object_or_404(Producto.objects.select_related('categoria', 'marca'), slug=slug, activo=True, mostrar_en_catalogo=True)
    relacionados = Producto.objects.filter(categoria=producto.categoria, activo=True, mostrar_en_catalogo=True).exclude(pk=producto.pk)[:4]
    return render(request, 'tienda/public/detalle_producto.html', {'producto': producto, 'relacionados': relacionados})


@require_POST
def agregar_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id, activo=True, mostrar_en_catalogo=True)
    cantidad = max(1, int(request.POST.get('cantidad', 1)))
    if not producto.permite_compra:
        messages.warning(request, 'Este producto está disponible solo para consulta.')
    elif producto.stock <= 0:
        messages.warning(request, 'Producto agotado.')
    elif cantidad > producto.stock:
        messages.warning(request, 'No hay stock suficiente para la cantidad solicitada.')
    else:
        session_add(request, producto, cantidad)
        messages.success(request, 'Producto agregado al carrito.')
    return redirect(request.POST.get('next') or 'tienda:carrito')


def carrito(request):
    items, subtotal = cart_items(request)
    return render(request, 'tienda/public/carrito.html', {'items': items, 'subtotal': subtotal, 'total': subtotal + ENVIO_DEFAULT})


@require_POST
def actualizar_carrito(request, producto_id):
    session_update(request, producto_id, request.POST.get('cantidad', 1))
    messages.success(request, 'Carrito actualizado.')
    return redirect('tienda:carrito')


@require_POST
def eliminar_carrito(request, producto_id):
    session_remove(request, producto_id)
    messages.success(request, 'Producto eliminado del carrito.')
    return redirect('tienda:carrito')


def checkout(request):
    items, subtotal = cart_items(request)
    if not items:
        messages.warning(request, 'Tu carrito está vacío.')
        return redirect('tienda:catalogo')
    total = subtotal + ENVIO_DEFAULT
    form = CheckoutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                locked_products = {p.id: p for p in Producto.objects.select_for_update().filter(id__in=[i['producto'].id for i in items])}
                for item in items:
                    product = locked_products[item['producto'].id]
                    if product.stock < item['cantidad'] or not product.disponible_para_compra:
                        raise ValueError(f'Stock no disponible para {product.nombre}.')
                cliente = ClientePedido.objects.create(**form.cleaned_data)
                pedido = Pedido.objects.create(
                    cliente=cliente,
                    usuario=request.user if request.user.is_authenticated else None,
                    subtotal=subtotal,
                    costo_envio=ENVIO_DEFAULT,
                    total=total,
                    estado=Pedido.Estado.RECIBIDO,
                    observaciones_cliente=form.cleaned_data.get('observaciones', ''),
                )
                for item in items:
                    producto = locked_products[item['producto'].id]
                    DetallePedido.objects.create(
                        pedido=pedido,
                        producto=producto,
                        nombre_producto_snapshot=producto.nombre,
                        codigo_sku_snapshot=producto.codigo_sku,
                        precio_unitario=producto.precio_actual,
                        cantidad=item['cantidad'],
                        subtotal=item['subtotal'],
                    )
                    producto.stock -= item['cantidad']
                    producto.save(update_fields=['stock', 'fecha_actualizacion'])
                clear_cart(request)
                messages.success(request, f'Su pedido fue registrado correctamente. Su número de pedido es: {pedido.codigo_pedido}. Guárdelo, ya que lo necesitará para consultar el estado de su compra y para subir su comprobante de transferencia.')
                return redirect('tienda:pago_transferencia', codigo_pedido=pedido.codigo_pedido)
        except ValueError as exc:
            messages.error(request, str(exc))
    return render(request, 'tienda/public/checkout.html', {'form': form, 'items': items, 'subtotal': subtotal, 'envio': ENVIO_DEFAULT, 'total': total})


def _pedido_por_contacto(codigo_pedido, contacto):
    return Pedido.objects.select_related('cliente').prefetch_related('detalles').filter(
        codigo_pedido__iexact=codigo_pedido.strip()
    ).filter(
        Q(cliente__email__iexact=contacto.strip()) | Q(cliente__telefono__iexact=contacto.strip())
    ).first()


def _puede_subir_comprobante(pedido):
    return pedido.estado_pago in [Pedido.EstadoPago.PENDIENTE, Pedido.EstadoPago.RECHAZADO]


def _guardar_comprobante_transferencia(form):
    pedido = form.save(commit=False)
    pedido.estado_pago = Pedido.EstadoPago.COMPROBANTE_RECIBIDO
    pedido.estado = Pedido.Estado.PAGO_EN_REVISION
    pedido.save()
    return pedido


def _contexto_publico_pedido(pedido, form=None, contacto=''):
    return {
        'pedido': pedido,
        'form': form or ComprobanteTransferenciaForm(instance=pedido),
        'cuentas': CuentaBancaria.objects.filter(activo=True),
        'puede_subir_comprobante': _puede_subir_comprobante(pedido),
        'contacto_consulta': contacto,
    }


def pago_transferencia(request, codigo_pedido):
    pedido = get_object_or_404(Pedido.objects.select_related('cliente').prefetch_related('detalles'), codigo_pedido=codigo_pedido)
    form = ComprobanteTransferenciaForm(request.POST or None, request.FILES or None, instance=pedido)
    if request.method == 'POST' and form.is_valid():
        pedido = _guardar_comprobante_transferencia(form)
        messages.success(request, 'Comprobante recibido. El administrador revisará y confirmará su pago.')
        return redirect('tienda:estado_pedido', codigo_pedido=pedido.codigo_pedido)
    return render(request, 'tienda/public/pago_transferencia.html', _contexto_publico_pedido(pedido, form))


def consultar_pedido(request):
    pedido = None
    form = None
    contacto = ''
    if request.method == 'POST':
        accion = request.POST.get('accion', 'buscar')
        codigo = request.POST.get('codigo_pedido', '').strip()
        contacto = request.POST.get('contacto', '').strip()
        pedido = _pedido_por_contacto(codigo, contacto)
        if not pedido:
            messages.error(request, 'No encontramos un pedido con esos datos. Verifique el código y el correo o teléfono utilizado en la compra.')
        elif accion == 'subir_comprobante':
            form = ComprobanteTransferenciaForm(request.POST, request.FILES, instance=pedido)
            if not _puede_subir_comprobante(pedido):
                messages.warning(request, 'Este pedido ya tiene un comprobante en revisión o un pago confirmado.')
            elif form.is_valid():
                pedido = _guardar_comprobante_transferencia(form)
                messages.success(request, 'Comprobante recibido correctamente. Su pago será revisado por el administrador.')
                form = ComprobanteTransferenciaForm(instance=pedido)
            else:
                messages.error(request, 'Revise el formulario de comprobante e intente nuevamente.')
    context = {'pedido': pedido, 'contacto_consulta': contacto}
    if pedido:
        context.update(_contexto_publico_pedido(pedido, form, contacto))
    return render(request, 'tienda/public/consulta_pedido.html', context)


def estado_pedido(request, codigo_pedido):
    pedido = get_object_or_404(Pedido.objects.select_related('cliente').prefetch_related('detalles'), codigo_pedido=codigo_pedido)
    return render(request, 'tienda/public/estado_pedido.html', _contexto_publico_pedido(pedido))


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    pedidos = Pedido.objects.all()
    return render(request, 'tienda/admin/dashboard.html', {
        'pedidos_dia': pedidos.filter(fecha_creacion__date=today).count(),
        'pendientes': pedidos.filter(estado__in=[Pedido.Estado.PENDIENTE, Pedido.Estado.RECIBIDO]).count(),
        'pagos_revision': pedidos.filter(Q(estado_pago=Pedido.EstadoPago.COMPROBANTE_RECIBIDO) | Q(estado=Pedido.Estado.PAGO_EN_REVISION)).count(),
        'ventas_mes': pedidos.filter(estado_pago=Pedido.EstadoPago.CONFIRMADO, fecha_creacion__date__gte=month_start).aggregate(s=Sum('total'))['s'] or 0,
        'productos_activos': Producto.objects.filter(activo=True).count(),
        'productos_agotados': Producto.objects.filter(stock=0).count(),
        'total_vendido': pedidos.filter(estado_pago=Pedido.EstadoPago.CONFIRMADO).aggregate(s=Sum('total'))['s'] or 0,
        'entregados': pedidos.filter(estado=Pedido.Estado.ENTREGADO).count(),
        'cancelados': pedidos.filter(estado=Pedido.Estado.CANCELADO).count(),
        'ultimos_pedidos': pedidos.select_related('cliente')[:8],
        'pagos_pendientes': pedidos.filter(estado_pago=Pedido.EstadoPago.COMPROBANTE_RECIBIDO).select_related('cliente')[:8],
    })


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_productos(request):
    return render(request, 'tienda/admin/productos/lista.html', {'productos': Producto.objects.select_related('categoria', 'marca')})


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_producto_form(request, pk=None):
    producto = get_object_or_404(Producto, pk=pk) if pk else None
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Producto guardado correctamente.')
        return redirect('tienda:admin_productos')
    return render(request, 'tienda/admin/productos/form.html', {'form': form, 'producto': producto})


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_producto_detalle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, 'tienda/admin/productos/detalle.html', {'producto': producto})


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_producto_toggle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = not producto.activo
    producto.save(update_fields=['activo', 'fecha_actualizacion'])
    messages.success(request, 'Estado del producto actualizado.')
    return redirect('tienda:admin_productos')


def _crud_list_form(request, model, form_class, template_list, template_form, redirect_name, pk=None):
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_class(request.POST or None, request.FILES or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Registro guardado correctamente.')
        return redirect(redirect_name)
    return render(request, template_form if pk or request.path.endswith('/crear/') else template_list, {'form': form, 'object': obj, 'items': model.objects.all()})


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_categorias(request):
    return _crud_list_form(request, CategoriaProducto, CategoriaProductoForm, 'tienda/admin/categorias/lista.html', 'tienda/admin/categorias/form.html', 'tienda:admin_categorias')


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_categoria_form(request, pk=None):
    return _crud_list_form(request, CategoriaProducto, CategoriaProductoForm, 'tienda/admin/categorias/lista.html', 'tienda/admin/categorias/form.html', 'tienda:admin_categorias', pk)


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_marcas(request):
    return _crud_list_form(request, MarcaProducto, MarcaProductoForm, 'tienda/admin/marcas/lista.html', 'tienda/admin/marcas/form.html', 'tienda:admin_marcas')


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_marca_form(request, pk=None):
    return _crud_list_form(request, MarcaProducto, MarcaProductoForm, 'tienda/admin/marcas/lista.html', 'tienda/admin/marcas/form.html', 'tienda:admin_marcas', pk)


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_pedidos(request):
    pedidos = Pedido.objects.select_related('cliente')
    if request.GET.get('estado'):
        pedidos = pedidos.filter(estado=request.GET['estado'])
    if request.GET.get('estado_pago'):
        pedidos = pedidos.filter(estado_pago=request.GET['estado_pago'])
    if request.GET.get('q'):
        q = request.GET['q']
        pedidos = pedidos.filter(Q(codigo_pedido__icontains=q) | Q(cliente__nombres__icontains=q) | Q(cliente__apellidos__icontains=q))
    return render(request, 'tienda/admin/pedidos/lista.html', {'pedidos': pedidos, 'estados': Pedido.Estado.choices, 'estados_pago': Pedido.EstadoPago.choices})


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_pedido_detalle(request, pk):
    pedido = get_object_or_404(Pedido.objects.select_related('cliente').prefetch_related('detalles'), pk=pk)
    estado_form = CambiarEstadoPedidoForm(request.POST or None, instance=pedido, prefix='estado')
    rechazo_form = RechazarPagoForm(request.POST or None, prefix='rechazo')
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'estado' and estado_form.is_valid():
            estado_form.save()
            messages.success(request, 'Pedido actualizado.')
        elif accion == 'confirmar_pago':
            pedido.estado_pago = Pedido.EstadoPago.CONFIRMADO
            pedido.estado = Pedido.Estado.PAGO_CONFIRMADO
            pedido.save(update_fields=['estado_pago', 'estado', 'fecha_actualizacion'])
            messages.success(request, 'Pago confirmado.')
        elif accion == 'rechazar_pago' and rechazo_form.is_valid():
            pedido.estado_pago = Pedido.EstadoPago.RECHAZADO
            pedido.observaciones_admin = rechazo_form.cleaned_data['observaciones_admin']
            if rechazo_form.cleaned_data['rechazar_pedido']:
                pedido.estado = Pedido.Estado.RECHAZADO
            pedido.save(update_fields=['estado_pago', 'estado', 'observaciones_admin', 'fecha_actualizacion'])
            messages.warning(request, 'Pago rechazado.')
        return redirect('tienda:admin_pedido_detalle', pk=pedido.pk)
    return render(request, 'tienda/admin/pedidos/detalle.html', {'pedido': pedido, 'estado_form': estado_form, 'rechazo_form': rechazo_form})


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_pagos_pendientes(request):
    pedidos = Pedido.objects.filter(Q(estado_pago=Pedido.EstadoPago.COMPROBANTE_RECIBIDO) | Q(estado=Pedido.Estado.PAGO_EN_REVISION)).select_related('cliente')
    return render(request, 'tienda/admin/pagos/pendientes.html', {'pedidos': pedidos})


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_cuentas(request):
    return _crud_list_form(request, CuentaBancaria, CuentaBancariaForm, 'tienda/admin/cuentas/lista.html', 'tienda/admin/cuentas/form.html', 'tienda:admin_cuentas')


@login_required
@grupo_requerido('Administrador', 'Tienda')
def admin_cuenta_form(request, pk=None):
    return _crud_list_form(request, CuentaBancaria, CuentaBancariaForm, 'tienda/admin/cuentas/lista.html', 'tienda/admin/cuentas/form.html', 'tienda:admin_cuentas', pk)


@login_required
@grupo_requerido('Administrador', 'Tienda', 'Ventas')
def admin_reportes(request):
    desde = request.GET.get('desde')
    hasta = request.GET.get('hasta')
    ventas = Pedido.objects.filter(estado_pago=Pedido.EstadoPago.CONFIRMADO)
    if desde:
        ventas = ventas.filter(fecha_creacion__date__gte=desde)
    if hasta:
        ventas = ventas.filter(fecha_creacion__date__lte=hasta)
    return render(request, 'tienda/admin/reportes.html', {
        'total_ventas': ventas.aggregate(s=Sum('total'))['s'] or 0,
        'pedidos_estado': Pedido.objects.values('estado').annotate(total=Count('id')),
        'mas_vendidos': DetallePedido.objects.values('nombre_producto_snapshot').annotate(cantidad=Sum('cantidad')).order_by('-cantidad')[:10],
        'bajo_stock': Producto.objects.filter(stock__lte=5).order_by('stock')[:20],
    })
