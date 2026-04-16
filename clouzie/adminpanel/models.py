from django.db import models
from django.utils.text import slugify

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
    category = models.ForeignKey(Category,on_delete=models.CASCADE,related_name="subcategory")
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
    
    category = models.ForeignKey(Category,on_delete=models.CASCADE)
    subcategory = models.ForeignKey(Subcategory,on_delete=models.CASCADE)
    
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

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

    def __str__(self):
        return f"{self.variant} Image"