from django.urls import path

from watcher import views


urlpatterns = [
    path('', views.index, name='index'),
    path('remove/<int:index>/', views.remove_repo, name='remove_repo'),  # Ensure this is present
]