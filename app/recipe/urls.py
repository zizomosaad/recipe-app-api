"""URL mappings for the recipe app"""

from django.urls import path, include

from rest_framework.routers import DefaultRouter
from recipe import views

router = DefaultRouter()  # we can use router here because it's a viewset not an apiview

router.register("recipes", views.RecipeViewSet)
router.register("tags", views.TagViewSet)
router.register("ingredients", views.IngredientViewSet)
app_name = "recipe"
urlpatterns = [path("", include(router.urls))]
