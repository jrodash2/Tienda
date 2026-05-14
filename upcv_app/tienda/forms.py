from django import forms
from .models import CategoriaProducto, MarcaProducto, Producto, ImagenProducto, Pedido, CuentaBancaria

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
            'codigo_sku', 'precio', 'precio_oferta', 'stock', 'imagen_principal', 'activo',
            'destacado', 'nuevo', 'mostrar_en_catalogo', 'permite_compra',
        ]
        widgets = {'descripcion_larga': forms.Textarea(attrs={'rows': 6})}

    def clean(self):
        cleaned = super().clean()
        precio = cleaned.get('precio')
        oferta = cleaned.get('precio_oferta')
        if oferta is not None and precio is not None and oferta >= precio:
            self.add_error('precio_oferta', 'El precio de oferta debe ser menor al precio regular.')
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
    direccion = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    departamento = forms.CharField(max_length=120)
    municipio = forms.CharField(max_length=120)
    nit = forms.CharField(max_length=30, required=False)
    observaciones = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', BOOTSTRAP_CLASS)


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


class CambiarEstadoPedidoForm(BootstrapModelForm):
    class Meta:
        model = Pedido
        fields = ['estado', 'observaciones_admin']
        widgets = {'observaciones_admin': forms.Textarea(attrs={'rows': 3})}


class RechazarPagoForm(forms.Form):
    observaciones_admin = forms.CharField(label='Motivo del rechazo', widget=forms.Textarea(attrs={'rows': 3, 'class': BOOTSTRAP_CLASS}))
    rechazar_pedido = forms.BooleanField(required=False, label='Marcar pedido como rechazado', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
