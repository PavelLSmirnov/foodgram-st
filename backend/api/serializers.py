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
from config.settings import MEDIA_URL
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

    def validate(self, data):
        if 'avatar' not in data:
            raise serializers.ValidationError({
                'avatar': ['Обязательное поле.']
            })
        return data


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta(DjoserUserSerializer.Meta):
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


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField(required=True)
    author = UserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    cooking_time = serializers.IntegerField(
        min_value=RECIPE_COOKING_TIME_MIN_VALUE,
        max_value=RECIPE_COOKING_TIME_MAX_VALUE
    )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        img_path = representation['image']
        if 'image' in representation and img_path:
            request = self.context.get('request')
            if request:
                representation['image'] = request.build_absolute_uri(img_path)
            else:
                representation['image'] = f"{MEDIA_URL}{img_path}"

        if self.context.get('request').method in ['POST', 'PUT', 'PATCH']:
            image_url = None

            if instance.image:
                image_url = request.build_absolute_uri(instance.image.url)

            return {
                "ingredients": IngredientInRecipeSerializer(
                    instance.recipe_ingredients.all(),
                    many=True,
                    context=self.context
                ).data,
                "image": image_url,
                "name": instance.name,
                "text": instance.text,
                "cooking_time": instance.cooking_time
            }

        return representation

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

    def update(self, instance, validated_data):
        instance.recipe_ingredients.all().delete()
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        self._create_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def validate(self, data):
        if not data.get('image'):
            raise serializers.ValidationError({
                "image": ["Обязательное поле."]
            })
        ingredients = data.get('recipe_ingredients', [])
        if not ingredients:
            raise serializers.ValidationError({
                "ingredients": ["Должен быть хотя бы один ингредиент."]
            })

        ingredient_ids = [item['ingredient'].id for item in ingredients]
        if len(set(ingredient_ids)) != len(ingredient_ids):
            raise serializers.ValidationError({
                "ingredients": ["Дублирование ингредиентов не допускается."]
            })

        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self._create_ingredients(recipe, ingredients_data)
        return recipe

    def _create_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['ingredient'],
                amount=ingredient['amount']
            ) for ingredient in ingredients_data
        ])
