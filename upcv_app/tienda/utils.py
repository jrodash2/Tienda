from decimal import Decimal, InvalidOperation


def formato_quetzales(value):
    """
    Formatea valores monetarios en quetzales.

    Ejemplos:
    2090 -> Q2,090.00
    150 -> Q150.00
    12500.5 -> Q12,500.50
    """
    if value is None or value == "":
        return "Q0.00"

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return "Q0.00"

    return f"Q{amount:,.2f}"
