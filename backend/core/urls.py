from django.urls import path

from .views import short_link

urlpatterns = [
    path(
        'rec/<int:pk>', short_link, name='short_link'),
]
