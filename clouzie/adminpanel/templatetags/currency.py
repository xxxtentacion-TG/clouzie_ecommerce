from decimal import Decimal, InvalidOperation

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def format_inr(value):
    """Format a number as Indian rupees without paise for admin summaries."""
    try:
        amount = Decimal(value or 0)
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")

    amount = amount.quantize(Decimal("1"))
    sign = "-" if amount < 0 else ""
    digits = str(abs(int(amount)))

    if len(digits) > 3:
        last_three = digits[-3:]
        remaining = digits[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        digits = ",".join(groups + [last_three])

    return f"{sign}₹{digits}"


@register.filter
def inr(value):
    return mark_safe(format_inr(value).replace("₹", "&#8377;"))
