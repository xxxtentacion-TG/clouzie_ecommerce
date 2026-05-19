from django.contrib import admin
from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 0
    readonly_fields = ('image',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('user', 'product', 'rating', 'is_verified_purchase', 'created_at')
    list_filter   = ('rating', 'is_verified_purchase')
    search_fields = ('user__username', 'product__name', 'comment')
    readonly_fields = ('created_at',)
    inlines = [ReviewImageInline]