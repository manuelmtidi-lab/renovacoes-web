from django.contrib import admin
from django.urls import include, path

from servicos import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", views.inicio, name="inicio"),
]
