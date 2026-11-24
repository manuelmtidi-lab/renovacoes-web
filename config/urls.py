from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from servicos import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("sw.js", TemplateView.as_view(template_name="pwa/sw.js", content_type="application/javascript"), name="sw"),
    path("manifest.json", TemplateView.as_view(template_name="pwa/manifest.json", content_type="application/manifest+json"), name="manifest"),
    path("offline/", TemplateView.as_view(template_name="offline.html"), name="offline"),
    path("", include("servicos.urls")),
    path("", views.inicio, name="inicio"),
]
