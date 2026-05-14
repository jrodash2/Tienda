# context_processors.py
from .models import FraseMotivacional
import random

def frase_del_dia(request):
    # Obtener todas las frases
    frases = FraseMotivacional.objects.all()
    
    # Verificar si hay frases disponibles
    if frases.exists():
        frase = random.choice(frases)
    else:
        # Si no hay frases, puedes devolver un valor predeterminado o None
        frase = None
    
    return {
        'frase_del_dia': frase
    }

def grupo_usuario(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'es_departamento': request.user.groups.filter(name='Departamento').exists(),
        'es_administrador': request.user.groups.filter(name='Administrador').exists(),
        'es_almacen': request.user.groups.filter(name='Almacen').exists(),
    }


from .models import Institucion

def datos_institucion(request):
    try:
        institucion = Institucion.objects.first()
    except Institucion.DoesNotExist:
        institucion = None

    return {
        'institucion': institucion
    }
