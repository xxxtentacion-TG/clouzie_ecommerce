from decimal import Decimal
from django.core.management.base import BaseCommand
from orders.models import OrderItem


class Command(BaseCommand):
    help = "Backfill offer_discount and original_price for existing OrderItems that have default 0 values."

    def handle(self, *args, **kwargs):
        # Get all items where original_price was never set (still 0)
        items = OrderItem.objects.filter(original_price=0).select_related("variant")
        total = items.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("All OrderItems already have offer data. Nothing to do."))
            return

        self.stdout.write(f"Backfilling {total} OrderItems...")

        updated = 0
        skipped = 0

        for item in items:
            if item.variant is None:
                skipped += 1
                continue

            # Use the variant's current price as the MRP (best approximation for historical orders)
            original_price = item.variant.price
            final_price    = item.price  # already stored as the offer-discounted price

            # Offer discount per item = (MRP - offer price) × quantity
            per_unit_discount = max(original_price - final_price, Decimal("0"))
            offer_discount    = per_unit_discount * item.quantity

            item.original_price = original_price
            item.offer_discount = offer_discount
            item.save(update_fields=["original_price", "offer_discount"])
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated: {updated}  |  Skipped (no variant): {skipped}"
            )
        )
