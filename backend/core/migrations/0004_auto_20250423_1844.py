from django.db import migrations
import csv
import os
from django.db import connection
from config.settings import BASE_DIR


def get_next_id(cursor, table_name):
    """Получаем следующий ID, который не вызовет конфликтов"""
    cursor.execute(f'SELECT MAX(id) FROM {table_name}')
    max_id = cursor.fetchone()[0] or 0
    return max_id + 1


def load_ingredients(apps, schema_editor):
    Ingredient = apps.get_model('core', 'Ingredient')

    csv_path = os.path.join(BASE_DIR, 'data', 'ingredients.csv')

    with connection.cursor() as cursor:
        next_id = get_next_id(cursor, 'core_ingredient')

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if not row or row[0].startswith('//'):
                    continue

                name = row[0].strip()
                measurement_unit = row[1].strip()

                # Если ингредиент с таким именем уже существует - пропускаем
                if Ingredient.objects.filter(name=name).exists():
                    continue

                # Создаём с явным указанием ID, который гарантированно не конфликтует
                Ingredient.objects.create(
                    id=next_id,
                    name=name,
                    measurement_unit=measurement_unit
                )
                next_id += 1


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20250423_1740'),
    ]

    operations = [
        migrations.RunPython(load_ingredients),
    ]
