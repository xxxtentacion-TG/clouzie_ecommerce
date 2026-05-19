from django.db import models
from django.conf import settings


class Review(models.Model):
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product      = models.ForeignKey('adminpanel.Products', on_delete=models.CASCADE, related_name='reviews')
    order_item   = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)
    rating       = models.IntegerField()
    comment      = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'order_item')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} – {self.product.name} ({self.rating}★)"


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image  = models.ImageField(upload_to='review_images/')

    def __str__(self):
        return f"Image for review {self.review_id}"