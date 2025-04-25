from django.contrib import admin
from django.contrib.auth import get_user_model
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource

from .models import (Favorite, Ingredient, Recipe, RecipeIngredient, ShopCart,
                     Subscription)

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'full_name')
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')

    @admin.display(description="ФИО")
    def full_name(self, obj):
        return obj.get_full_name()


class IngredientResource(ModelResource):
    class Meta:
        model = Ingredient
        exclude = ('id',)
        skip_first_row = True
        encoding = 'utf-8-sig'
        import_mode = 1
        import_id_fields = []


@admin.register(Ingredient)
class IngredientAdmin(ImportExportModelAdmin):
    resource_class = IngredientResource
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ['ingredient']


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    search_fields = ('name', 'author__username')
    list_filter = ('author',)
    inlines = [RecipeIngredientInline]
    readonly_fields = ('favorites_count',)

    fieldsets = (
        (None, {
            'fields': ('name', 'author', 'image', 'text', 'cooking_time')
        }),
        ('Дополнительная информация', {
            'fields': ('favorites_count',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='В избранном')
    def favorites_count(self, obj):
        return obj.favorites.count()


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    list_filter = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')


@admin.register(Favorite, ShopCart)
class UserRecipeRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')
