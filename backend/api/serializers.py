from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer as DjoserUserSerializer
from django.contrib.auth import get_user_model
from core.models import (Ingredient, Recipe, RecipeIngredient,
                         Favorite, ShopCart, Subscription)
from core.constants import (MAX_RECIPES_LIMIT,
                            RECIPE_INGREDIENT_AMOUNT_MIN_VALUE,
                            RECIPE_INGREDIENT_AMOUNT_MAX_VALUE,
                            RECIPE_COOKING_TIME_MIN_VALUE,
                            RECIPE_COOKING_TIME_MAX_VALUE)

User = get_user_model()


class BaseActionSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для действий с рецептами (избранное, корзина)."""
    class Meta:
        abstract = True

    def validate(self, data):
        user = self.context['request'].user
        recipe = self.context['recipe']
        verbose_name = self.Meta.model._meta.verbose_name

        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'status': f'Рецепт уже в {verbose_name}'}
            )
        return data

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        return {
            'id': instance.recipe.id,
            'name': instance.recipe.name,
            'author': instance.recipe.author.username
        }


class FavoriteSerializer(BaseActionSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        read_only_fields = ('user',)


class ShopCartSerializer(BaseActionSerializer):
    class Meta:
        model = ShopCart
        fields = ('user', 'recipe')
        read_only_fields = ('user',)


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['user', 'author']

    def validate(self, data):
        user = self.context['request'].user
        author = data['author']

        if user == author:
            raise serializers.ValidationError(
                'Действие невозможно для самого себя'
            )

        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError('Вы уже подписаны')

        return data

    def to_representation(self, instance):
        return {
            'status': 'Подписка успешно добавлена',
            'author': instance.author.username,
            'user': instance.user.username
        }


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, author):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and author.subscribers.filter(user=request.user).exists())


class SiteUserSerializer(UserSerializer):
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )
    recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, author):
        request = self.context.get('request')
        try:
            recipes_limit = int(request.GET.get(
                'recipes_limit', MAX_RECIPES_LIMIT))
        except ValueError:
            recipes_limit = MAX_RECIPES_LIMIT

        return RecipeShortSerializer(
            author.recipes.all()[:recipes_limit],
            many=True,
            context=self.context
        ).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сокращенный сериализатор для рецептов (используется в подписках)."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(
        min_value=RECIPE_INGREDIENT_AMOUNT_MIN_VALUE,
        max_value=RECIPE_INGREDIENT_AMOUNT_MAX_VALUE
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для рецептов."""
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='recipe_ingredients',
        many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'author', 'ingredients', 'is_favorited',
                  'is_in_shopping_cart', 'name', 'image', 'text',
                  'cooking_time')

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and obj.favorites.filter(user=request.user).exists())

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and obj.shopcarts.filter(user=request.user).exists())


class RecipeReadSerializer(RecipeBaseSerializer):
    """Сериализатор для чтения рецептов."""
    pass


class RecipeWriteSerializer(RecipeBaseSerializer):
    """Сериализатор для создания/обновления рецептов."""
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=RECIPE_COOKING_TIME_MIN_VALUE,
        max_value=RECIPE_COOKING_TIME_MAX_VALUE
    )

    def validate(self, data):
        ingredients = data.get('recipe_ingredients', [])
        if not ingredients:
            raise serializers.ValidationError(
                "Должен быть хотя бы один ингредиент.")

        ingredient_ids = [
            ingredient['ingredient'].id for ingredient in ingredients]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise serializers.ValidationError(
                "Дублирование ингредиентов не допускается.")

        if not data.get('image'):
            raise serializers.ValidationError(
                "Поле 'image' не может быть пустым.")

        return data

    def create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            ) for ingredient in ingredients_data
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = super().create(validated_data)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)


class RecipeSerializer(serializers.ModelSerializer):
    """Основной сериализатор рецептов с динамическим представлением."""

    def to_representation(self, instance):
        view = self.context.get('view')
        action = self.context['view'].action
        if view and action in ['create', 'update']:
            return RecipeWriteSerializer(instance, context=self.context).data
        return RecipeReadSerializer(instance, context=self.context).data

    class Meta:
        model = Recipe
        fields = '__all__'
