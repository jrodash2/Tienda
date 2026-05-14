from django.contrib import admin
from .models import (
   FraseMotivacional
)

# Crea una clase que personaliza la vista en el admin
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')  # Qué campos mostrar en la lista
    search_fields = ('frase', 'personaje')  # Habilitar búsqueda por estos campos
    ordering = ('personaje',)  # Ordenar por el campo 'personaje'

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)

# R

