from django import template

from tienda.utils import formato_quetzales

register = template.Library()


@register.filter
def quetzales(value):
    """
    Formatea valores monetarios en quetzales.

    Ejemplos:
    2090 -> Q2,090.00
    150 -> Q150.00
    12500.5 -> Q12,500.50
    """
    return formato_quetzales(value)
