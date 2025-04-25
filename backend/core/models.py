from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models

from .constants import (AVATAR_UPLOAD_PATH,
                        INGREDIENT_MEASUREMENT_UNIT_MAX_LENGTH,
                        INGREDIENT_NAME_MAX_LENGTH,
                        RECIPE_COOKING_TIME_MIN_VALUE,
                        RECIPE_IMAGE_UPLOAD_PATH,
                        RECIPE_INGREDIENT_AMOUNT_MIN_VALUE,
                        RECIPE_NAME_MAX_LENGTH, USER_EMAIL_MAX_LENGTH,
                        USER_FIRST_NAME_MAX_LENGTH, USER_LAST_NAME_MAX_LENGTH,
                        USER_USERNAME_MAX_LENGTH)


class SiteUser(AbstractUser):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    avatar = models.ImageField(
        upload_to=AVATAR_UPLOAD_PATH,
        blank=True,
        null=True,
        verbose_name='Аватарка',
    )
    email = models.EmailField(
        max_length=USER_EMAIL_MAX_LENGTH,
        unique=True,
        verbose_name='Электронная почта',
    )
    username = models.CharField(
        max_length=USER_USERNAME_MAX_LENGTH,
        blank=True,
        null=True,
        verbose_name='Никнейм',
    )
    first_name = models.CharField(
        max_length=USER_FIRST_NAME_MAX_LENGTH,
        verbose_name='Имя',
    )
    last_name = models.CharField(
        max_length=USER_LAST_NAME_MAX_LENGTH,
        verbose_name='Фамилия',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['username']

    def __str__(self):
        return self.username

    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class Ingredient(models.Model):
    name = models.CharField(
        max_length=INGREDIENT_NAME_MAX_LENGTH,
        verbose_name='Название',
    )
    measurement_unit = models.CharField(
        max_length=INGREDIENT_MEASUREMENT_UNIT_MAX_LENGTH,
        verbose_name='Ед. измерения',
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_name_measurement_unit',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.measurement_unit})'


User = get_user_model()


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор',
    )
    name = models.CharField(
        max_length=RECIPE_NAME_MAX_LENGTH,
        verbose_name='Название',
    )
    image = models.ImageField(
        upload_to=RECIPE_IMAGE_UPLOAD_PATH,
        verbose_name='Изображение',
    )
    text = models.TextField(
        verbose_name='Описание',
    )
    cooking_time = models.PositiveIntegerField(
        validators=[MinValueValidator(RECIPE_COOKING_TIME_MIN_VALUE)],
        verbose_name='Время приготовления (мин)',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/recipes/{self.pk}'


class BaseUserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(class)s_user_recipe',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} -> {self.recipe.name}'


class Favorite(BaseUserRecipeRelation):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )

    class Meta(BaseUserRecipeRelation.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'


class ShopCart(BaseUserRecipeRelation):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopcarts',
        verbose_name='Рецепт'
    )

    class Meta(BaseUserRecipeRelation.Meta):
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Пользователь',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name='Автор',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_user_author',
            ),
        ]
        ordering = ['user']
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f'{self.user.username} подписан на {self.author.username}'


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Ингредиент',
    )
    amount = models.IntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(RECIPE_INGREDIENT_AMOUNT_MIN_VALUE)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient',
            ),
        ]
        ordering = ['recipe']
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецептов'

    def __str__(self):
        return f'{self.amount} {self.ingredient} в {self.recipe.name}'
