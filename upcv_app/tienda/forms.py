from django import forms
from .models import CategoriaProducto, MarcaProducto, Producto, ImagenProducto, Pedido, CuentaBancaria, UbicacionTienda

BOOTSTRAP_CLASS = 'form-control'


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else BOOTSTRAP_CLASS
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            field.widget.attrs.setdefault('class', css)


class CategoriaProductoForm(BootstrapModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'slug', 'descripcion', 'imagen', 'activo', 'orden']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class MarcaProductoForm(BootstrapModelForm):
    class Meta:
        model = MarcaProducto
        fields = ['nombre', 'slug', 'logo', 'activo']


class ProductoForm(BootstrapModelForm):
    class Meta:
        model = Producto
        fields = [
            'categoria', 'marca', 'nombre', 'slug', 'descripcion_corta', 'descripcion_larga',
            'codigo_sku', 'precio', 'precio_oferta', 'stock', 'costo_envio', 'imagen_principal', 'activo',
            'destacado', 'nuevo', 'mostrar_en_catalogo', 'permite_compra',
        ]
        widgets = {'descripcion_larga': forms.Textarea(attrs={'rows': 6})}

    def clean(self):
        cleaned = super().clean()
        precio = cleaned.get('precio')
        oferta = cleaned.get('precio_oferta')
        costo_envio = cleaned.get('costo_envio')
        if oferta is not None and precio is not None and oferta >= precio:
            self.add_error('precio_oferta', 'El precio de oferta debe ser menor al precio regular.')
        if costo_envio is not None and costo_envio < 0:
            self.add_error('costo_envio', 'El costo de envío no puede ser negativo.')
        return cleaned


class ImagenProductoForm(BootstrapModelForm):
    class Meta:
        model = ImagenProducto
        fields = ['imagen', 'alt', 'orden']


class CheckoutForm(forms.Form):
    nombres = forms.CharField(max_length=120)
    apellidos = forms.CharField(max_length=120)
    telefono = forms.CharField(max_length=30)
    email = forms.EmailField()
    tipo_entrega = forms.ChoiceField(choices=Pedido.TipoEntrega.choices, initial=Pedido.TipoEntrega.ENVIO_DOMICILIO, widget=forms.RadioSelect)
    direccion = forms.CharField(label='Dirección de entrega', widget=forms.Textarea(attrs={'rows': 3}), required=False)
    departamento = forms.CharField(label='Departamento de entrega', max_length=120, required=False)
    municipio = forms.CharField(label='Municipio de entrega', max_length=120, required=False)
    ubicacion_recogida = forms.ModelChoiceField(queryset=UbicacionTienda.objects.none(), required=False, empty_label='Seleccione una ubicación')
    nit = forms.CharField(max_length=30, required=False)
    observaciones = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ubicacion_recogida'].queryset = UbicacionTienda.objects.filter(activo=True)
        for name, field in self.fields.items():
            if name == 'tipo_entrega':
                field.widget.attrs.setdefault('class', 'delivery-radio')
            else:
                css = 'form-select' if isinstance(field.widget, forms.Select) else BOOTSTRAP_CLASS
                field.widget.attrs.setdefault('class', css)

    def clean(self):
        cleaned = super().clean()
        tipo_entrega = cleaned.get('tipo_entrega')
        if tipo_entrega == Pedido.TipoEntrega.ENVIO_DOMICILIO:
            for field in ['direccion', 'departamento', 'municipio']:
                if not cleaned.get(field):
                    self.add_error(field, 'Este campo es obligatorio para envío a domicilio.')
            cleaned['ubicacion_recogida'] = None
        elif tipo_entrega == Pedido.TipoEntrega.RECOGER_TIENDA:
            if not cleaned.get('ubicacion_recogida'):
                self.add_error('ubicacion_recogida', 'Seleccione una ubicación para recoger su pedido.')
        else:
            self.add_error('tipo_entrega', 'Seleccione una forma de entrega válida.')
        return cleaned


class ComprobanteTransferenciaForm(BootstrapModelForm):
    class Meta:
        model = Pedido
        fields = ['comprobante_transferencia', 'banco_origen', 'numero_referencia', 'fecha_transferencia']
        widgets = {
            'comprobante_transferencia': forms.ClearableFileInput(attrs={'accept': 'image/*,.pdf'}),
            'fecha_transferencia': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comprobante_transferencia'].required = True
        self.fields['comprobante_transferencia'].help_text = 'Adjunte una imagen o PDF del comprobante de transferencia.'


class CuentaBancariaForm(BootstrapModelForm):
    class Meta:
        model = CuentaBancaria
        fields = ['banco', 'nombre_cuenta', 'numero_cuenta', 'tipo_cuenta', 'moneda', 'instrucciones', 'activo', 'orden']
        widgets = {'instrucciones': forms.Textarea(attrs={'rows': 4})}


class UbicacionTiendaForm(BootstrapModelForm):
    class Meta:
        model = UbicacionTienda
        fields = ['nombre', 'direccion', 'departamento', 'municipio', 'telefono', 'horario', 'google_maps_url', 'activo', 'orden']
        widgets = {'direccion': forms.Textarea(attrs={'rows': 4})}


class CambiarEstadoPedidoForm(BootstrapModelForm):
    class Meta:
        model = Pedido
        fields = ['estado', 'observaciones_admin']
        widgets = {'observaciones_admin': forms.Textarea(attrs={'rows': 3})}


class RechazarPagoForm(forms.Form):
    observaciones_admin = forms.CharField(label='Motivo del rechazo', widget=forms.Textarea(attrs={'rows': 3, 'class': BOOTSTRAP_CLASS}))
    rechazar_pedido = forms.BooleanField(required=False, label='Marcar pedido como rechazado', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
