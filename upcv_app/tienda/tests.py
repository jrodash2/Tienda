from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from tienda.models import CategoriaProducto, Cliente, CotizacionPOS, DetalleCotizacionPOS, PagoVenta, Producto
from tienda.services.pos_service import crear_venta_pos


class VentaGananciasPOSTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username='vendedor', password='test')
        self.categoria = CategoriaProducto.objects.create(nombre='General')
        self.cliente = Cliente.objects.create(nombre='Consumidor final')

    def crear_producto(self, precio_costo):
        return Producto.objects.create(
            categoria=self.categoria,
            nombre=f'Producto costo {precio_costo}',
            codigo_sku=f'SKU-{precio_costo}',
            precio=Decimal('120.00'),
            precio_costo=Decimal(precio_costo),
            stock=10,
        )

    def test_pago_completo_calcula_ganancias_y_estado(self):
        producto = self.crear_producto('80.00')
        venta = crear_venta_pos(
            usuario=self.usuario,
            cliente=self.cliente,
            items=[{'producto_id': producto.id, 'cantidad': 1}],
            monto_pagado=Decimal('120.00'),
            tipo_pago='completo',
        )

        self.assertEqual(venta.total, Decimal('120.00'))
        self.assertEqual(venta.total_pagado, Decimal('120.00'))
        self.assertEqual(venta.costo_total, Decimal('80.00'))
        self.assertEqual(venta.ganancia_bruta, Decimal('40.00'))
        self.assertEqual(venta.ganancia_cobrada, Decimal('40.00'))
        self.assertEqual(venta.saldo_pendiente, Decimal('0.00'))
        self.assertEqual(venta.estado, 'pagado')

    def test_pago_parcial_calcula_ganancia_cobrada_proporcional(self):
        producto = self.crear_producto('80.00')
        venta = crear_venta_pos(
            usuario=self.usuario,
            cliente=self.cliente,
            items=[{'producto_id': producto.id, 'cantidad': 1}],
            monto_pagado=Decimal('100.00'),
            tipo_pago='parcial',
        )

        self.assertEqual(venta.total, Decimal('120.00'))
        self.assertEqual(venta.total_pagado, Decimal('100.00'))
        self.assertEqual(venta.costo_total, Decimal('80.00'))
        self.assertEqual(venta.ganancia_bruta, Decimal('40.00'))
        self.assertEqual(venta.ganancia_cobrada.quantize(Decimal('0.01')), Decimal('33.33'))
        self.assertEqual(venta.saldo_pendiente, Decimal('20.00'))
        self.assertEqual(venta.estado, 'pagado_parcial')

    def test_venta_sin_costo_queda_detectable_para_alerta(self):
        producto = self.crear_producto('0.00')
        venta = crear_venta_pos(
            usuario=self.usuario,
            cliente=self.cliente,
            items=[{'producto_id': producto.id, 'cantidad': 1}],
            monto_pagado=Decimal('120.00'),
            tipo_pago='completo',
        )

        self.assertEqual(venta.costo_total, Decimal('0.00'))
        self.assertEqual(venta.ganancia_bruta, Decimal('120.00'))
        self.assertTrue(venta.tiene_detalles_sin_costo)
        self.assertEqual(PagoVenta.objects.filter(venta=venta).count(), 1)


    def test_cotizacion_no_descuenta_stock_y_convierte_una_sola_vez(self):
        producto = self.crear_producto('80.00')
        stock_inicial = producto.stock
        cotizacion = CotizacionPOS.objects.create(cliente=self.cliente, usuario=self.usuario)
        DetalleCotizacionPOS.objects.create(
            cotizacion=cotizacion,
            producto=producto,
            cantidad=2,
            precio_unitario=producto.precio_actual,
            precio_costo_unitario=producto.precio_costo,
        )

        producto.refresh_from_db()
        self.assertEqual(producto.stock, stock_inicial)
        self.assertEqual(cotizacion.total, Decimal('240.00'))
        self.assertEqual(cotizacion.nombre_vendedor, 'vendedor')


class TemplateOrderingTests(SimpleTestCase):
    def test_base_admin_tienda_extends_is_first_template_tag(self):
        from pathlib import Path

        template_path = Path(__file__).resolve().parent / 'templates' / 'tienda' / 'admin' / '_base_admin_tienda.html'
        first_line = template_path.read_text(encoding='utf-8').splitlines()[0]
        self.assertEqual(first_line, "{% extends 'almacen/base.html' %}")
