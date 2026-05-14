from .cart import SESSION_KEY


def carrito_context(request):
    carrito = request.session.get(SESSION_KEY, {})
    total_items = 0
    for item in carrito.values():
        try:
            total_items += int(item.get('cantidad', 0))
        except (TypeError, ValueError):
            continue
    return {'carrito_total_items': total_items}
