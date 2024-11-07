from django.urls import path

from watcher.views import index


urlpatterns = [
    path('', index),
]