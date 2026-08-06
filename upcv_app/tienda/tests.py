import json
from decimal import Decimal

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from tienda.models import CategoriaProducto, Cliente, CotizacionPOS, DetalleCotizacionPOS, PagoVenta, Producto
from tienda.services.pos_service import agregar_pago_venta, crear_venta_pos


class VentaGananciasPOSTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username='vendedor', password='test')
        self.usuario.groups.add(Group.objects.get(name='Ventas'))
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

    def test_venta_credito_descuenta_stock_sin_crear_pago(self):
        producto = self.crear_producto('80.00')
        venta = crear_venta_pos(
            usuario=self.usuario,
            cliente=self.cliente,
            items=[{'producto_id': producto.id, 'cantidad': 2}],
            monto_pagado=Decimal('0.00'),
            tipo_pago='credito',
        )

        producto.refresh_from_db()
        self.assertEqual(producto.stock, 8)
        self.assertEqual(venta.estado, 'credito')
        self.assertEqual(venta.total, Decimal('240.00'))
        self.assertEqual(venta.total_pagado, Decimal('0.00'))
        self.assertEqual(venta.saldo_pendiente, Decimal('240.00'))
        self.assertEqual(venta.ganancia_bruta, Decimal('80.00'))
        self.assertEqual(venta.ganancia_cobrada, Decimal('0.00'))
        self.assertFalse(PagoVenta.objects.filter(venta=venta).exists())

    def test_venta_credito_pasa_a_parcial_y_pagada_con_pagos_posteriores(self):
        producto = self.crear_producto('80.00')
        venta = crear_venta_pos(
            usuario=self.usuario,
            cliente=self.cliente,
            items=[{'producto_id': producto.id, 'cantidad': 1}],
            tipo_pago='credito',
        )

        agregar_pago_venta(venta=venta, usuario=self.usuario, monto=Decimal('20.00'))
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'pagado_parcial')
        self.assertEqual(venta.saldo_pendiente, Decimal('100.00'))

        agregar_pago_venta(venta=venta, usuario=self.usuario, monto=Decimal('100.00'))
        venta.refresh_from_db()
        self.assertEqual(venta.estado, 'pagado')
        self.assertEqual(venta.saldo_pendiente, Decimal('0.00'))

    def test_endpoint_registra_credito_y_devuelve_respuesta_esperada(self):
        producto = self.crear_producto('80.00')
        self.client.force_login(self.usuario)

        response = self.client.post(
            reverse('tienda:pos_api_ventas_crear'),
            data=json.dumps({
                'cliente_id': self.cliente.id,
                'items': [{'producto_id': producto.id, 'cantidad': 1}],
                'pago': {
                    'tipo': 'credito',
                    'monto': '0.00',
                    'metodo_pago': '',
                    'referencia': '',
                    'observaciones': 'Venta registrada al crédito',
                },
            }),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['estado'], 'credito')
        self.assertEqual(data['pagado'], '0.00')
        self.assertEqual(data['saldo'], '120.00')
        self.assertEqual(data['mensaje'], 'Venta registrada al crédito correctamente.')
        self.assertFalse(PagoVenta.objects.filter(venta_id=data['venta_id']).exists())

    def test_api_clientes_busca_por_dpi_y_devuelve_json_completo(self):
        Cliente.objects.create(
            nombre='María López', telefono='55551234', email='maria@example.com',
            nit='1234-5', dpi='1234567890101', direccion='Ciudad de Guatemala',
        )
        self.client.force_login(self.usuario)

        response = self.client.get(
            reverse('tienda:pos_api_clientes_buscar'),
            {'q': '1234567890101'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['clientes']), 1)
        self.assertEqual(data['clientes'][0]['nombre'], 'María López')
        self.assertEqual(data['clientes'][0]['direccion'], 'Ciudad de Guatemala')

    def test_api_clientes_busca_nombre_parcial_sin_distinguir_mayusculas(self):
        Cliente.objects.create(nombre='Julio Rene', telefono='42161234')
        self.client.force_login(self.usuario)

        for termino in ('Julio', 'julio', 'Rene', 'rene', '4216'):
            with self.subTest(termino=termino):
                response = self.client.get(
                    reverse('tienda:pos_api_clientes_buscar'),
                    {'q': termino},
                    HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                )
                self.assertEqual(response.status_code, 200)
                clientes = response.json()['clientes']
                self.assertEqual([cliente['nombre'] for cliente in clientes], ['Julio Rene'])

    def test_api_clientes_crea_y_devuelve_cliente_seleccionable(self):
        self.client.force_login(self.usuario)
        payload = {
            'nombre': 'Carlos Pérez', 'telefono': '44445555',
            'email': 'carlos@example.com', 'nit': 'CF',
            'dpi': '9876543210101', 'direccion': 'Mixco',
        }

        response = self.client.post(
            reverse('tienda:pos_api_clientes_crear'),
            data=json.dumps(payload), content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['cliente']['dpi'], payload['dpi'])
        self.assertEqual(data['cliente']['direccion'], payload['direccion'])
        self.assertTrue(Cliente.objects.filter(pk=data['cliente']['id'], nombre='Carlos Pérez').exists())

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

    def test_pos_javascript_registra_eventos_mediante_helper_seguro(self):
        from pathlib import Path

        js_path = Path(__file__).resolve().parent.parent / 'static' / 'tienda' / 'js' / 'pos.js'
        javascript = js_path.read_text(encoding='utf-8')
        self.assertIn('function agregarEventoSeguro(id, evento, funcion)', javascript)
        self.assertIn('if (!elemento)', javascript)
        self.assertNotIn("$('btnPagoCompleto').addEventListener", javascript)
        self.assertNotIn("$('btnGuardarCliente').addEventListener", javascript)
        self.assertNotIn("$('btnGuardarCotizacion').addEventListener", javascript)
