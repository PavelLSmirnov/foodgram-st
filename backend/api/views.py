from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Sum
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from djoser.views import UserViewSet as DjoserUserViewSet
from core.models import (Ingredient, Recipe, RecipeIngredient,
                         Favorite, ShopCart, Subscription)
from .serializers import (IngredientSerializer, RecipeSerializer,
                          UserSerializer, AvatarSerializer,
                          SiteUserSerializer, ShopCartSerializer,
                          FavoriteSerializer, SubscriptionSerializer
                          )
from .permissions import IsAuthorOrReadOnly

from .get_shopping_cart_text import get_shopping_cart_text
from .pagination import RecipePagination

User = get_user_model()


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = RecipePagination

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Фильтрация по автору
        author_id = self.request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author__id=author_id)

        # Фильтрация по корзине покупок
        if self.request.query_params.get('is_in_shopping_cart') == '1':
            if user.is_authenticated:
                queryset = queryset.filter(shopcarts__user=user)

        # Фильтрация по избранному
        if self.request.query_params.get('is_favorited') == '1':
            if user.is_authenticated:
                queryset = queryset.filter(favorites__user=user)

        return queryset.order_by('-pub_date').distinct()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @staticmethod
    def handle_favorite_or_cart(request, model, serializer_class, pk):
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == 'POST':
            data = {'user': user.id, 'recipe': recipe.id}
            serializer = serializer_class(
                data=data, context={'request': request, 'recipe': recipe})

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(
                    serializer.data, status=status.HTTP_201_CREATED)

            return Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        deleted, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(
            {'status': 'Рецепт не найден'},
            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        return self.handle_favorite_or_cart(
            request, ShopCart, ShopCartSerializer, pk)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        return self.handle_favorite_or_cart(
            request, Favorite, FavoriteSerializer, pk)

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        user = request.user
        ingredients = (
            RecipeIngredient.objects
            .filter(recipe__shopcarts__user=user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(total_amount=Sum('amount'))
            .order_by('ingredient__name')
        )
        recipes = Recipe.objects.filter(shopcarts__user=user)
        shopping_cart_text = get_shopping_cart_text(user, ingredients, recipes)
        return FileResponse(shopping_cart_text,
                            as_attachment=True,
                            filename='shopping_cart.txt',
                            content_type='text/plain')

    @action(detail=True, methods=['get'], url_path='get-link')
    def short_link(self, request, pk=None):
        recipe = self.get_object()
        short_url = request.build_absolute_uri(
            reverse('short_link', args=[recipe.pk]))
        return Response({'short-link': short_url}, status=status.HTTP_200_OK)


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"

    @action(detail=False, methods=['put', 'delete'],
            permission_classes=[permissions.IsAuthenticated],
            url_path='me/avatar')
    def avatar(self, request):
        user = request.user

        if request.method == 'DELETE':
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response(
                    {'avatar': None}, status=status.HTTP_204_NO_CONTENT)
            raise ValidationError({'error': 'Аватар отсутствует'})

        serializer = AvatarSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_object(self):
        if self.action == "me":
            return self.request.user
        return super().get_object()

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        subscriptions = Subscription.objects.filter(
            user=request.user).select_related('author')
        authors = [sub.author for sub in subscriptions]
        page = self.paginate_queryset(authors)
        serializer = SiteUserSerializer(page, many=True,
                                        context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True,
            methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if user == author:
            raise ValidationError({
                'errors': 'Действие невозможно для самого себя'
            })

        if request.method == 'POST':
            # Передаем данные в сериализатор
            serializer = SubscriptionSerializer(
                data={'user': user.id, 'author': author.id},
                context={'request': request}
            )

            # Сериализатор сам выполнит валидацию
            serializer.is_valid(raise_exception=True)

            # Если валидация прошла, сохраняем подписку
            subscription = serializer.save()
            return Response(
                {'status': 'Подписка успешно добавлена'},
                status=status.HTTP_201_CREATED
            )

        subscription = get_object_or_404(
            Subscription,
            user=user,
            author=author
        )
        subscription.delete()
        return Response(
            {'status': 'Вы успешно отписались'},
            status=status.HTTP_204_NO_CONTENT
        )
