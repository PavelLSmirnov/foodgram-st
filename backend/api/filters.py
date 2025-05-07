from django_filters import rest_framework
from core.models import Ingredient
from django_filters.rest_framework import FilterSet

class IngredientFilter(FilterSet):
    name = rest_framework.CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ("name",)
