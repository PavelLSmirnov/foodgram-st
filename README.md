# Foodgram Project


Фудграм — сайт, на котором пользователи могут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также доступен сервис «Список покупок». Он позволяет создавать список продуктов, которые нужно купить для приготовления выбранных блюд.


## Структура проекта

Проект включает следующие страницы:
- Главная страница
- Страница входа
- Страница регистрации
- Страница рецепта
- Страница пользователя
- Страница подписок
- Избранное
- Список покупок
- Создание и редактирование рецепта
- Страница смены пароля
- Статические страницы: «О проекте» и «Технологии»

## Начало работы

1. **Клонирование репозитория**

   Для начала работы с проектом необходимо клонировать репозиторий:

   ```bash
   git clone https://github.com/PavelLSmirnov/foodgram-st.git
   ```

2. **Настройка окружения**

    настройте конфигурацию проекта для этого можете скопировать .env.example и поменять данные в файле .env
   ```bash
   cp .env.example .env
   ```

3. **Запуск проекта**

   В директории `infra`:

   ```bash
   docker compose up -d
   ```

4. **Cоздание суперпольователя**

   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

# Запуск бекэнда в режиме разработки
   1. **Перейти в папку backend**

   ```bash
      cd backend
   ```

   2. **Создать и активировать виртуальное окружение**

   ```bash
      python -m venv env
      source env/bin/actiavate
   ```
   
   3.  **Установить зависимости для python 3.13**
   
   ```bash
      pip install -r reqirements.txt
   ```

   4. **Создать .env файл с параметрами**

   ```env
      SECRET_KEY=4f56bf4e-c037-4845-9c3f-eb4181395f3c
      DEBUG=True
      ALLOWED_HOSTS=localhost,127.0.0.1,backend,frontend
      # параметры POSTGRES и DB не указываются для работы с sqlite3 
   ```

   5. **Запустить миграции**

   ```bash
      python manage.py migrate
   ```

   6. **Запуск сервера разработки**

   ```bash
      python manage.py runserver
   ```

## Доступ к приложению

- Веб-интерфейс: [Localhost](http://localhost/)
- API документация: [Localhost docs](http://localhost/api/docs/)
- Админ-панель: [Localhost admin](http://localhost/admin/)
