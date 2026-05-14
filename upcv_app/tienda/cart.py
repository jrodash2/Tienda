from decimal import Decimal
from .models import Producto

SESSION_KEY = 'tienda_carrito'


def get_cart(request):
    return request.session.setdefault(SESSION_KEY, {})


def save_cart(request, cart):
    request.session[SESSION_KEY] = cart
    request.session.modified = True


def add_to_cart(request, producto, cantidad=1):
    cart = get_cart(request)
    key = str(producto.pk)
    current = int(cart.get(key, {}).get('cantidad', 0))
    new_qty = min(current + int(cantidad), producto.stock)
    cart[key] = {'cantidad': new_qty}
    save_cart(request, cart)


def update_cart(request, producto_id, cantidad):
    cart = get_cart(request)
    key = str(producto_id)
    if int(cantidad) <= 0:
        cart.pop(key, None)
    else:
        producto = Producto.objects.get(pk=producto_id)
        cart[key] = {'cantidad': min(int(cantidad), producto.stock)}
    save_cart(request, cart)


def remove_from_cart(request, producto_id):
    cart = get_cart(request)
    cart.pop(str(producto_id), None)
    save_cart(request, cart)


def clear_cart(request):
    request.session[SESSION_KEY] = {}
    request.session.modified = True


def cart_items(request):
    cart = get_cart(request)
    productos = Producto.objects.filter(pk__in=cart.keys(), activo=True)
    items = []
    subtotal = Decimal('0.00')
    for producto in productos:
        cantidad = int(cart[str(producto.pk)].get('cantidad', 1))
        cantidad = min(cantidad, producto.stock)
        precio = producto.precio_actual
        line_total = precio * cantidad
        subtotal += line_total
        items.append({'producto': producto, 'cantidad': cantidad, 'precio': precio, 'subtotal': line_total})
    return items, subtotal
