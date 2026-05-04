from django.db import models
from django.utils.text import slugify
import uuid
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100,unique=True)
    slug = models.SlugField(unique=True,blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_deleted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug

            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class Subcategory(models.Model):
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="subcategories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('category', 'name')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category.name})"
    
    
class Products(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    
    description = models.TextField(blank=True,null=True)
    materials = models.TextField(blank=True,null=True)
    care_guide = models.TextField(blank=True,null=True)
    delivery = models.TextField(blank=True,null=True)
    payment_returns = models.TextField(blank=True,null=True)
    
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="category")
    subcategory = models.ForeignKey(Subcategory,on_delete=models.CASCADE,related_name="products")
    
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
class Variants(models.Model):
    
    SIZE_CHOICES = [
    ("S", "Small"),
    ("M", "Medium"),
    ("L", "Large"),
    ("XL", "Extra Large"),
]

    COLOR_CHOICES = [
        ("Red", "Red"),
        ("Blue", "Blue"),
        ("Black", "Black"),
        ("White", "White"),
        ("Light blue", "Light blue"),
        ("Maroon", "Maroon"),
        ("Dark green", "Dark green"),
    ]
    
    product = models.ForeignKey(Products,on_delete=models.CASCADE,related_name="variants")
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    size = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=50, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        unique_together = ('product', 'size', 'color')
    def save(self, *args, **kwargs):

        if not self.sku:
            self.sku = f"{self.product.id}-{self.size}-{self.color}".upper()

        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} - {self.size} - {self.color}"
    
    
    
class VariantImage(models.Model):
    variant = models.ForeignKey(Variants,on_delete=models.CASCADE,related_name="images")
    image = models.ImageField(upload_to="variants/")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f"{self.variant} Image"
    
    
from django.db import models


class Coupon(models.Model):

    DISCOUNT_TYPE_CHOICES = (
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
    )

    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES
    )

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    min_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    max_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    usage_limit_per_user = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code
    
    def is_valid(self):
        now = timezone.now().date()
        return self.is_active and not self.is_deleted and self.start_date <= now <= self.end_date
    
    
class Offer(models.Model):

    OFFER_TYPE = (
        ("PRODUCT", "Product"),
        ("CATEGORY", "Category"),
        ("SUBCATEGORY", "Subcategory"),
    )

    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE)

    product = models.ForeignKey("products.Product", null=True, blank=True, on_delete=models.CASCADE)
    category = models.ForeignKey("products.Category", null=True, blank=True, on_delete=models.CASCADE)
    subcategory = models.ForeignKey("products.SubCategory", null=True, blank=True, on_delete=models.CASCADE)

    discount_type = models.CharField(max_length=10, choices=[("PERCENTAGE", "Percentage"), ("FIXED", "Fixed")])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)