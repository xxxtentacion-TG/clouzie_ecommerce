from decimal import Decimal
from django.utils import timezone
from adminpanel.models import Offer

def get_best_offer(product, base_price):
    today = timezone.now().date()

    best_discount = Decimal("0.00")
    best_percentage = Decimal("0.00")

    offers = Offer.objects.filter(
        is_active=True,
        is_deleted=False,
        start_date__lte=today,
        end_date__gte=today
    )

    for offer in offers:
        if not (
            offer.product == product or
            offer.category == product.category or
            offer.subcategory == product.subcategory
        ):
            continue

        if offer.discount_type == "PERCENTAGE":
            discount = (base_price * offer.discount_value) / Decimal("100")
            percentage = offer.discount_value
        else:
            discount = offer.discount_value
            percentage = (discount / base_price) * 100 if base_price > 0 else 0

        if discount > best_discount:
            best_discount = discount
            best_percentage = percentage

    final_price = base_price - best_discount

    return max(final_price, Decimal("0.00")), best_discount, best_percentage