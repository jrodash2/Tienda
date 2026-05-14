from django.db import transaction
from decimal import Decimal
import pandas as pd
import math  # Para manejar NaN en floats
from almacen_app.models import (
    form1h, Proveedor, Articulo, DetalleFactura, Categoria, UnidadDeMedida,
    Ubicacion, LineaLibre
)
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Carga masiva de productos desde un archivo Excel'

    def add_arguments(self, parser):
        parser.add_argument('archivo_excel', type=str, help='Ruta al archivo Excel')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        archivo = kwargs['archivo_excel']
        df = pd.read_excel(archivo)

        if df.empty:
            self.stdout.write(self.style.ERROR('El archivo está vacío.'))
            return

        # Agrupar por numero_factura
        facturas = df.groupby('numero_factura')

        for numero_factura, grupo in facturas:
            self.stdout.write(f'Procesando factura: {numero_factura}')
            self.stdout.write(f'Número de detalles para la factura {numero_factura}: {len(grupo)}')

            f1h = form1h.objects.filter(numero_factura=numero_factura).first()

            if not f1h:
                first_row = grupo.iloc[0]
                proveedor_nombre = first_row.get('proveedor', '') or ''
                proveedor, _ = Proveedor.objects.get_or_create(nombre=proveedor_nombre)

                f1h = form1h.objects.create(
                    proveedor=proveedor,
                    numero_factura=numero_factura,
                    estado=first_row.get('estado', 'borrador'),
                    fecha_ingreso=first_row.get('fecha_ingreso'),
                    orden_compra=first_row.get('orden_compra'),
                    nit_proveedor=first_row.get('nit_proveedor'),
                    proveedor_nombre=proveedor_nombre,
                    telefono_proveedor=first_row.get('telefono_proveedor'),
                    direccion_proveedor=first_row.get('direccion_proveedor'),
                    patente=first_row.get('patente'),
                    fecha_factura=first_row.get('fecha_factura'),
                    serie_id=first_row.get('serie_id'),
                    dependencia_id=first_row.get('dependencia_id'),
                    programa_id=first_row.get('programa_id'),
                )

            numero_serie = f1h.numero_serie

            for _, row in grupo.iterrows():
                categoria, _ = Categoria.objects.get_or_create(nombre=row.get('categoria', 'Sin Categoría'))

                unidad_nombre = row.get('unidad_medida', 'UND')
                unidad, _ = UnidadDeMedida.objects.get_or_create(
                    nombre=unidad_nombre,
                    defaults={'simbolo': unidad_nombre[:3]}
                )

                ubicacion_nombre = row.get('ubicacion', 'Principal')
                ubicacion, _ = Ubicacion.objects.get_or_create(nombre=ubicacion_nombre)

                articulo_nombre = row.get('articulo', 'Sin Nombre')
                articulo, _ = Articulo.objects.get_or_create(
                    nombre=articulo_nombre,
                    defaults={'categoria': categoria, 'unidad_medida': unidad, 'ubicacion': ubicacion}
                )

                # === Manejo de fecha_vencimiento ===
                fecha_raw = row.get('fecha_vencimiento')
                fecha_vencimiento = None

                if not pd.isna(fecha_raw) and str(fecha_raw).strip() not in ["", "00:00:00"]:
                    try:
                        fecha_vencimiento = pd.to_datetime(fecha_raw, dayfirst=True).strftime('%Y-%m-%d')
                        articulo.requiere_vencimiento = True
                        articulo.save()
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(
                            f"Error al procesar la fecha de vencimiento: {fecha_raw}, error: {e}"
                        ))
                        fecha_vencimiento = None

                # === Manejo seguro de cantidad ===
                cantidad_raw = row.get('cantidad', 0)
                if pd.isna(cantidad_raw) or (isinstance(cantidad_raw, float) and math.isnan(cantidad_raw)):
                    cantidad = 0
                else:
                    cantidad = int(float(cantidad_raw))

              
                # === Manejo seguro de precio_unitario ===
                precio_str = str(row.get('precio_unitario', '0')).replace(',', '').strip()
                try:
                    precio_unitario = Decimal(precio_str or '0')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'Error al convertir precio_unitario \"{precio_str}\" a Decimal: {e}'
                    ))
                    precio_unitario = Decimal('0')


                detalle_existente = DetalleFactura.objects.filter(
                    form1h=f1h,
                    articulo=articulo
                ).first()

                if detalle_existente:
                    detalle_existente.cantidad += cantidad
                    detalle_existente.precio_unitario = precio_unitario
                    detalle_existente.precio_total = detalle_existente.cantidad * precio_unitario
                    detalle_existente.fecha_vencimiento = fecha_vencimiento
                    detalle_existente.save()
                    self.stdout.write(f'Actualizado detalle para artículo {articulo.nombre}')
                else:
                    DetalleFactura.objects.create(
                        form1h=f1h,
                        articulo=articulo,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        precio_total=cantidad * precio_unitario,
                        id_linea=articulo.id,
                        renglon=articulo.id,
                        fecha_vencimiento=fecha_vencimiento,
                    )
                    self.stdout.write(f'Nuevo detalle creado para artículo {articulo.nombre}')

            if f1h.estado not in ['borrador', 'confirmado', 'anulado']:
                f1h.estado = 'borrador'
            f1h.save()

            self.stdout.write(self.style.SUCCESS(
                f'Factura {numero_factura} cargada con estado "{f1h.estado}".'
            ))
