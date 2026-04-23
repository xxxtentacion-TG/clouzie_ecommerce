from django.db import models
from accounts.models import CustomUser
from adminpanel.models import Variants
# Create your models here.
class Wishlist(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name="wishlist_items")
    variant = models.ForeignKey(Variants,on_delete=models.CASCADE,related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user','variant')
    def __str__(self):
        return f"{self.user} - {self.variant}"
    
    
        