from django.utils.timezone import now
from django.contrib.auth import get_user_model

User = get_user_model()


def generate_shopping_list_header():
    return f'Список покупок на {now().strftime('%d-%m-%Y %H:%M:%S')}\n'


def format_ingredient_line(index, ingredient):
    meas_unit = ingredient['ingredient__measurement_unit']
    total_amount = ingredient['total_amount']
    return (
        f'{index}. {ingredient['ingredient__name'].capitalize()} '
        f'({meas_unit}) - {total_amount}'
    )


def format_recipe_line(recipe):
    return f'- {recipe.name} (@{recipe.author.username})'


def get_shopping_cart_text(user, ingredients, recipes):
    """
    Генерирует текстовое представление списка покупок.

    Args:
        user: Пользователь, для которого формируется список
        ingredients: Список ингредиентов с количеством
        recipes: Рецепты, для которых формируется список

    Returns:
        str: Отформатированный текст списка покупок
    """
    sections = [
        generate_shopping_list_header(),
        'Продукты:\n',
        *(format_ingredient_line(idx, item)
          for idx, item in enumerate(ingredients, start=1)),
        '\nРецепты для продуктов:\n',
        *(format_recipe_line(recipe) for recipe in recipes)
    ]

    return '\n'.join(sections)
