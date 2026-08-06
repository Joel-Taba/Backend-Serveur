from django.contrib import admin

from .models import Category, Document


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "slug", "created_at"]
    list_filter = ["parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "doc_type", "size", "uploaded_by", "created_at"]
    list_filter = ["doc_type", "category"]
    search_fields = ["title"]
    readonly_fields = ["doc_type", "size"]
