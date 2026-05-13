from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from decimal import Decimal
User = settings.AUTH_USER_MODEL


class Wallet(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="wallet"
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} Wallet - ₹{self.balance}"
    
    def credit(self, amount, description="", order=None):

        amount = Decimal(str(amount))

        # Convert existing balance safely
        self.balance = Decimal(str(self.balance))

        self.balance += amount
        self.save()

        WalletTransaction.objects.create(
            wallet=self,
            order=order,
            type="CREDIT",
            amount=amount,
            description=description,
            status="SUCCESS"
        )

    def debit(self, amount, description="", order=None):

        amount = Decimal(str(amount))

        self.balance = Decimal(str(self.balance))

        if self.balance < amount:
            raise ValueError("Insufficient balance")

        self.balance -= amount
        self.save()

        WalletTransaction.objects.create(
            wallet=self,
            order=order,
            type="DEBIT",
            amount=amount,
            description=description,
            status="SUCCESS"
        )
        
        
class WalletTransaction(models.Model):

    TRANSACTION_TYPE = [
        ("CREDIT", "Credit"),
        ("DEBIT", "Debit"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    ]

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    order = models.ForeignKey(
        "orders.Order",   # adjust if your app name differs
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPE
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="SUCCESS"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.wallet.user} - {self.type} - ₹{self.amount}"
    
    
    