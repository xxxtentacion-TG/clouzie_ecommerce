from django.db import models
from django.conf import settings
import uuid
from decimal import Decimal

class Order(models.Model):

    PAYMENT_METHODS = (
        ('COD',       'Cash on Delivery'),
        ('RAZORPAY',  'Razorpay'),
        ('WALLET',    'Wallet'),
    )

    PAYMENT_STATUS = (
        ('PENDING',  'Pending'),
        ('PAID',     'Paid'),
        ('FAILED',   'Failed'),
        ('REFUNDED', 'Refunded'),
    )

    ORDER_STATUS = (
        ('PENDING',          'Pending'),
        ('CONFIRMED',        'Confirmed'),
        ('PACKED',           'Packed'),
        ('SHIPPED',          'Shipped'),
        ('DELIVERED',        'Delivered'),
        ('CANCELLED',        'Cancelled'),
        ('PARTIALLY_CANCELLED', 'Partially Cancelled'),
        ('PARTIALLY_RETURNED', 'Partially Returned'),
        ('RETURN_REQUESTED', 'Return Requested'),
        ('RETURNED',         'Returned'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    address = models.ForeignKey(
        'accounts.Address',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    coupon_code        = models.CharField(max_length=50, null=True, blank=True)
    uuid               = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order_id           = models.CharField(max_length=30, unique=True)
    razorpay_order_id  = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)

    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='COD')
    payment_status  = models.CharField(max_length=20, choices=PAYMENT_STATUS,  default='PENDING')
    order_status    = models.CharField(max_length=20, choices=ORDER_STATUS,     default='PENDING')

    subtotal          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_discount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # original coupon, never mutated
    tax_amount        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_charge   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    placed_at      = models.DateTimeField(auto_now_add=True)
    delivered_date = models.DateTimeField(null=True, blank=True)
    updated_at     = models.DateTimeField(auto_now=True)
    original_subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    @property
    def display_total(self):
        """Amount to display to the user.
        - CANCELLED orders: show original paid amount (not 0) for user clarity.
        - All other states: show the live, recalculated total_amount.
        """
        if self.order_status == 'CANCELLED':
            from decimal import Decimal
            original = self.original_subtotal or self.subtotal or Decimal('0.00')
            coupon   = self.coupon_discount   or Decimal('0.00')
            delivery = self.delivery_charge   or Decimal('0.00')
            return max(original - coupon + delivery, Decimal('0.00'))
        return self.total_amount

    def recalculate(self):
        active_items = self.items.exclude(status__in=['CANCELLED', 'RETURNED'])

        self.subtotal = sum(i.total for i in active_items)
        self.original_subtotal = sum(i.original_price * i.quantity for i in active_items)
        self.discount_amount = sum(i.offer_discount for i in active_items)

        # 🔥 IMPORTANT: use ORIGINAL stored coupon (never mutate it)
        original_coupon = self.coupon_discount or Decimal("0.00")
        original_subtotal = self.original_subtotal or self.subtotal

        if not active_items.exists():
            # ✅ FULL CANCEL FIX
            self.tax_amount = Decimal("0.00")
            self.total_amount = Decimal("0.00")
        else:
            if original_subtotal > 0 and original_coupon > 0:
                ratio = self.subtotal / original_subtotal
                effective_coupon = (original_coupon * ratio).quantize(Decimal("0.01"))
            else:
                effective_coupon = Decimal("0.00")

            self.tax_amount = Decimal("0.00")

            self.total_amount = max(
                self.subtotal - effective_coupon + self.delivery_charge,
                Decimal("0.00")
            )

        self.save(update_fields=[
            'subtotal',
            'original_subtotal',
            'discount_amount',
            'tax_amount',
            'total_amount',
            'updated_at'
        ])
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order_status == "DELIVERED":
            self.items.exclude(status__in=["CANCELLED", "RETURNED"]).update(status="DELIVERED")

        elif self.order_status == "SHIPPED":
            self.items.exclude(status__in=["CANCELLED", "RETURNED"]).update(status="SHIPPED")

        elif self.order_status == "CONFIRMED":
            self.items.exclude(status__in=["CANCELLED", "RETURNED"]).update(status="CONFIRMED")
    def __str__(self):
        return self.order_id


class OrderItem(models.Model):

    STATUS_CHOICES = (
    ('PENDING', 'Pending'),
    ('CONFIRMED', 'Confirmed'),
    ('SHIPPED', 'Shipped'),
    ('DELIVERED', 'Delivered'),
    ('CANCELLED', 'Cancelled'),
    ('RETURN_REQUESTED', 'Return Requested'),
    ('RETURNED', 'Returned'),
)

    order   = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        'adminpanel.Variants', on_delete=models.SET_NULL, null=True, blank=True
    )

    product_name = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=255)

    original_price = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    price          = models.DecimalField(max_digits=10, decimal_places=2)             
    offer_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0) 
    quantity       = models.PositiveIntegerField(default=1)
    total          = models.DecimalField(max_digits=10, decimal_places=2)

    status     = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
 
    @property
    def has_review(self):
        return self.review_set.exists()
    def __str__(self):
        return f"{self.product_name} - {self.order.order_id}"


class ReturnRequest(models.Model):

    RETURN_REASONS = (
        ('WRONG_SIZE',   'Wrong size'),
        ('DAMAGED',      'Damaged item'),
        ('WRONG_ITEM',   'Wrong item received'),
        ('QUALITY',      'Quality issue'),
        ('CHANGED_MIND', 'Changed mind'),
        ('BETTER_PRICE', 'Better price elsewhere'),
        ('OTHER',        'Other'),
    )

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='return_requests'
    )
    order_item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name='return_request', null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='return_requests'
    )
    reason      = models.CharField(max_length=30, choices=RETURN_REASONS)
    notes       = models.TextField(blank=True)
    image       = models.ImageField(upload_to='return_images/', null=True, blank=True)
    status      = models.CharField(max_length=20,default='PENDING')
    admin_notes = models.TextField(blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    FINAL_STATES = {'REJECTED', 'CLOSED', 'REFUNDED'}
    ALLOWED_TRANSITIONS = {
        'PENDING':  ['APPROVED', 'REJECTED'],
        'APPROVED': ['RECEIVED', 'REFUNDED', 'CLOSED'],
        'RECEIVED': ['REFUNDED', 'CLOSED'],
        'REFUNDED': ['CLOSED'],
        'REJECTED': [],
        'CLOSED':   [],
    }

    def __str__(self):
        return f"Return #{self.id} - {self.order.order_id}"