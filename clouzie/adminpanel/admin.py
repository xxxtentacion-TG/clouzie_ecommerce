from django.contrib import admin
from .models import Category, Subcategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active', 'is_deleted', 'created_at']
    list_filter = ['is_active', 'is_deleted']
    search_fields = ['name']
    prepopulated_fields = {"slug": ("name",)}
    ordering = ['-created_at']


@admin.register(Subcategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'is_active', 'is_deleted', 'created_at']
    list_filter = ['category', 'is_active', 'is_deleted']
    search_fields = ['name', 'category__name']
    autocomplete_fields = ['category']   # 🔥 dropdown search
    ordering = ['-created_at']