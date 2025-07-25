"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.shortcuts import redirect
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Service Commandes DDD API",
        default_version="v1",
        description="""
        **Service Commandes - Architecture DDD (Domain-Driven Design)**
        
        Ce service gère les commandes clients selon les principes DDD avec des Use Cases métier.
        
        **Architecture DDD :**
        • Domain Layer : Entités, Value Objects, Règles métier
        • Application Layer : Use Cases orientés fonctionnalités
        • Infrastructure Layer : Repositories, Services externes
        • Interface Layer : APIs REST orientées métier
        
        **Use Cases disponibles :**
        • Enregistrer une commande (validation métier complète)
        • Annuler une commande (avec restauration stock)
        • Générer indicateurs de performance par magasin
        • Produire rapport consolidé par magasin
        
        **Communication avec autres services :**
        • Service Catalogue (port 8001) : informations produits
        • Service Stock (port 8002) : validation et gestion stocks
        
        **Endpoints DDD :**
        • `POST /api/v1/ventes-ddd/enregistrer/` - Use Case: Enregistrer Commande
        • `PATCH /api/v1/ventes-ddd/{id}/annuler/` - Use Case: Annuler Commande
        • `GET /api/v1/indicateurs/` - Use Case: Générer Indicateurs
        • `GET /api/v1/rapport-consolide/` - Use Case: Rapport Consolidé
        """,
        terms_of_service="https://www.example.com/policies/terms/",
        contact=openapi.Contact(email="admin@lab430.ca"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


def redirect_to_swagger(request):
    """Redirection automatique vers Swagger"""
    return redirect("schema-swagger-ui")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", redirect_to_swagger, name="home"),  # Redirection automatique
    path("api/v1/", include("ventes.ddd_urls")),
    # Documentation Swagger
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]
