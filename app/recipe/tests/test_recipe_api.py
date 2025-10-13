"""Test recipe APIs."""  # File docstring describing the purpose of the file

import tempfile
import os

from PIL import Image

from decimal import Decimal  # Import Decimal for precise price values

from django.contrib.auth import (
    get_user_model,
)  # Import function to get the custom user model
from django.test import TestCase  # Import Django's test case class
from django.urls import reverse  # Import reverse to build URLs from route names

from rest_framework import status  # Import HTTP status codes
from rest_framework.test import APIClient  # Import DRF's APIClient for API testing

from core.models import (
    Recipe,
    Tag,
    Ingredient,
)  # Import Recipe, Tag, Ingredient models from core app

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
)  # Import serializers for recipes

RECIPES_URL = reverse(
    "recipe:recipe-list"
)  # Build the URL for the recipe list endpoint


def detail_url(recipe_id):
    """Create and return a recipe detail URL."""  # Docstring for the helper function
    return reverse(
        "recipe:recipe-detail", args=[recipe_id]
    )  # Build the detail URL for a specific recipe


def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


def create_recipe(user, **params):
    """Helper function that creates and returns a new recipe"""  # Docstring for the helper function

    defaults = {
        "title": "Sample recipe title",  # Default title for the recipe
        "time_minutes": 22,  # Default time in minutes
        "price": Decimal("5.25"),  # Default price using Decimal
        "description": "Sample description",  # Default description
        "link": "http://example.com/recipe.pdf",  # Default link
    }
    defaults.update(params)  # Update defaults with any provided parameters

    recipe = Recipe.objects.create(
        user=user, **defaults
    )  # Create a new Recipe object with the user and defaults
    return recipe  # Return the created recipe


def create_user(**params):
    """Create and return a new user"""  # Docstring for the helper function
    return get_user_model().objects.create_user(
        **params
    )  # Create and return a new user using the custom user model


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests."""  # Docstring for the test class

    def setUp(self):
        self.client = APIClient()  # Set up the API client for making requests

    def test_auth_required(self):
        """Test auth is required to call API."""  # Docstring for the test
        res = self.client.get(RECIPES_URL)  # Make a GET request to the recipes endpoint

        self.assertEqual(
            res.status_code, status.HTTP_401_UNAUTHORIZED
        )  # Assert that the response status is 401


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests."""  # Docstring for the test class

    def setUp(self):
        self.client = APIClient()  # Set up the API client
        self.user = create_user(
            email="user@example.com", password="testpass123"
        )  # Create a test user

        self.client.force_authenticate(
            self.user
        )  # Authenticate the client with the test user

    def test_retrieve_recipes(self):
        """Test retrieving user's list of recipes."""  # Docstring for the test
        create_recipe(user=self.user)  # Create a recipe for the user
        create_recipe(user=self.user)  # Create another recipe for the user

        res = self.client.get(RECIPES_URL)  # Make a GET request to the recipes endpoint

        recipes = Recipe.objects.all().order_by(
            "-id"
        )  # Get all recipes ordered by id descending
        serializer = RecipeSerializer(recipes, many=True)  # Serialize the recipes

        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200
        self.assertEqual(
            res.data, serializer.data
        )  # Assert that the response data matches the serialized data

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""  # Docstring for the test
        other_user = create_user(
            email="otheruser@exmaple.com", password="testpass321"
        )  # Create another user

        create_recipe(user=other_user)  # Create a recipe for the other user
        create_recipe(user=self.user)  # Create a recipe for the authenticated user

        res = self.client.get(RECIPES_URL)  # Make a GET request to the recipes endpoint

        recipes = Recipe.objects.filter(
            user=self.user
        )  # Filter recipes by the authenticated user
        serializer = RecipeSerializer(
            recipes, many=True
        )  # Serialize the filtered recipes
        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200
        self.assertEqual(
            res.data, serializer.data
        )  # Assert that the response data matches the serialized data

    def test_get_recipe_detail(self):
        """Test get recipe detail"""  # Docstring for the test

        recipe = create_recipe(user=self.user)  # Create a recipe for the user

        url = detail_url(recipe.id)  # Build the detail URL for the recipe
        res = self.client.get(url)  # Make a GET request to the recipe detail endpoint

        serializer = RecipeDetailSerializer(
            recipe
        )  # Serialize the recipe with the detail serializer
        self.assertEqual(
            res.data, serializer.data
        )  # Assert that the response data matches the serialized data
        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200

    def test_create_recipe(self):
        """Test creating a recipe"""  # Docstring for the test

        payload = {
            "title": "Sample recipe",  # Title for the new recipe
            "time_minutes": 30,  # Time in minutes for the new recipe
            "price": Decimal("5.99"),  # Price for the new recipe
        }
        res = self.client.post(
            RECIPES_URL, payload
        )  # Make a POST request to create a recipe
        self.assertEqual(
            res.status_code, status.HTTP_201_CREATED
        )  # Assert that the response status is 201
        recipe = Recipe.objects.get(
            id=res.data["id"]
        )  # Get the created recipe from the database

        for k, v in payload.items():  # Loop through the payload items
            self.assertEqual(
                getattr(recipe, k), v
            )  # Assert that each field matches the payload
        self.assertEqual(
            recipe.user, self.user
        )  # Assert that the recipe user is the authenticated user

    def test_partial_update(self):
        """Test partial update of a recipe"""  # Docstring for the test
        original_link = "https://example.com/recipe.pdf"  # Store the original link
        recipe = create_recipe(
            user=self.user, title="Sample recipe title", link=original_link
        )  # Create a recipe with a specific link

        payload = {
            "title": "New recipe title",  # New title for the recipe
        }
        url = detail_url(recipe_id=recipe.id)  # Build the detail URL for the recipe
        res = self.client.patch(
            url, payload
        )  # Make a PATCH request to update the recipe

        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200
        recipe.refresh_from_db()  # Refresh the recipe from the database
        self.assertEqual(
            recipe.title, payload["title"]
        )  # Assert that the title was updated
        self.assertEqual(
            recipe.link, original_link
        )  # Assert that the link was not changed
        self.assertEqual(
            recipe.user, self.user
        )  # Assert that the user is still the authenticated user

    def test_full_update(self):
        """Test full update of recipe."""  # Docstring for the test

        recipe = create_recipe(
            user=self.user,
            title="Sample recipe title",
            link="https://example.com/recipe.pdf",
            description="Sample recipe description",
        )  # Create a recipe with specific fields

        payload = {
            "title": "New title",  # New title for the recipe
            "link": "https://example.com/new-recipe.pdf",  # New link for the recipe
            "description": "New recipe description",  # New description
            "time_minutes": 10,  # New time in minutes
            "price": Decimal("2.50"),  # New price
        }

        url = detail_url(recipe_id=recipe.id)  # Build the detail URL for the recipe
        res = self.client.put(
            url, payload
        )  # Make a PUT request to fully update the recipe

        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200
        recipe.refresh_from_db()  # Refresh the recipe from the database
        for k, v in payload.items():  # Loop through the payload items
            self.assertEqual(
                getattr(recipe, k), v
            )  # Assert that each field matches the payload
        self.assertEqual(
            recipe.user, self.user
        )  # Assert that the user is still the authenticated user

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error"""  # Docstring for the test
        new_user = create_user(
            email="user2@example.com", password="test123"
        )  # Create a new user
        recipe = create_recipe(
            user=self.user
        )  # Create a recipe for the authenticated user

        payload = {"user": new_user.id}  # Attempt to change the user of the recipe
        url = detail_url(recipe.id)  # Build the detail URL for the recipe
        res = self.client.patch(
            url, payload
        )  # Make a PATCH request to update the recipe

        recipe.refresh_from_db()  # Refresh the recipe from the database
        self.assertEqual(recipe.user, self.user)  # Assert that the user was not changed

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""  # Docstring for the test

        recipe = create_recipe(
            user=self.user
        )  # Create a recipe for the authenticated user

        url = detail_url(recipe.id)  # Build the detail URL for the recipe
        res = self.client.delete(url)  # Make a DELETE request to delete the recipe

        self.assertEqual(
            res.status_code, status.HTTP_204_NO_CONTENT
        )  # Assert that the response status is 204
        self.assertFalse(
            Recipe.objects.filter(id=recipe.id).exists()
        )  # Assert that the recipe no longer exists

    def test_delete_other_user_recipe_error(self):
        """Test deleting a recipe successful."""  # Docstring for the test

        new_user = create_user(
            email="user2@example.com", password="test123"
        )  # Create a new user
        recipe = create_recipe(user=new_user)  # Create a recipe for the new user

        url = detail_url(recipe.id)  # Build the detail URL for the recipe
        res = self.client.delete(url)  # Make a DELETE request to delete the recipe

        self.assertEqual(
            res.status_code, status.HTTP_404_NOT_FOUND
        )  # Assert that the response status is 404
        self.assertTrue(
            Recipe.objects.filter(id=recipe.id).exists()
        )  # Assert that the recipe still exists

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags"""  # Docstring for the test

        payload = {
            "title": "Thai Prawn Curry",  # Title for the new recipe
            "time_minutes": 30,  # Time in minutes
            "price": Decimal("2.50"),  # Price
            "tags": [{"name": "Thai"}, {"name": "Dinner"}],  # List of new tags
        }
        res = self.client.post(
            RECIPES_URL, payload, format="json"
        )  # Make a POST request to create the recipe with tags

        self.assertEqual(
            res.status_code, status.HTTP_201_CREATED
        )  # Assert that the response status is 201

        recipes = Recipe.objects.filter(
            user=self.user
        )  # Get the created recipe for the user
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        for tag in payload["tags"]:  # Loop through the tags in the payload
            exists = recipe.tags.filter(
                name=tag["name"], user=self.user
            ).exists()  # Check if the tag exists for the user
            self.assertTrue(exists)  # Assert that the tag exists

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tags"""  # Docstring for the test

        tag1 = Tag.objects.create(
            user=self.user, name="Indian"
        )  # Create an existing tag for the user
        payload = {
            "title": "Pongal",  # Title for the new recipe
            "time_minutes": 60,  # Time in minutes
            "price": Decimal("4.50"),  # Price
            "tags": [
                {"name": "Indian"},
                {"name": "Breakfast"},
            ],  # List of tags (one existing, one new)
        }
        res = self.client.post(
            RECIPES_URL, payload, format="json"
        )  # Make a POST request to create the recipe with tags
        self.assertEqual(
            res.status_code, status.HTTP_201_CREATED
        )  # Assert that the response status is 201
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]  # Get the created recipe for the user
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag1, recipe.tags.all())
        for tag in payload["tags"]:  # Loop through the tags in the payload
            exists = recipe.tags.filter(
                name=tag["name"], user=self.user
            ).exists()  # Check if the tag exists for the user
            self.assertTrue(exists)  # Assert that the tag exists

    def test_create_tag_on_update(self):
        """Test creating new tag when update recipe."""  # Docstring for the test

        recipe = create_recipe(user=self.user)  # Create a recipe for the user
        payload = {"tags": [{"name": "Lunch"}]}  # New tag to be added
        url = detail_url(recipe.id)  # Build the detail URL for the recipe
        res = self.client.patch(
            url, payload, format="json"
        )  # Make a PATCH request to update the recipe with a new tag

        self.assertEqual(
            res.status_code, status.HTTP_200_OK
        )  # Assert that the response status is 200
        new_tag = Tag.objects.get(
            user=self.user, name="Lunch"
        )  # Get the newly created tag for the user
        self.assertIn(
            new_tag, recipe.tags.all()
        )  # Assert that the new tag is linked to the recipe

    def test_clear_recipe_tags(self):
        """Test clear recipe tag"""

        tag = Tag.objects.create(user=self.user, name="Dessert")  # Create a tag
        recipe = create_recipe(user=self.user)  # Create a recipe
        recipe.tags.add(tag)  # Add the tag to the recipe

        payload = {"tags": []}  # Payload to clear tags

        url = detail_url(recipe.id)  # Get recipe detail URL
        res = self.client.patch(url, payload, format="json")  # Send PATCH request

        self.assertEqual(res.status_code, status.HTTP_200_OK)  # Check response status
        recipe.refresh_from_db()  # Refresh recipe from database
        self.assertEqual(recipe.tags.count(), 0)  # Assert tags are cleared

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with new ingredients"""
        payload = {
            "title": "Coriander eggs on toast",
            "time_minutes": 30,
            "price": Decimal("5.50"),
            "ingredients": [{"name": "Coriander"}, {"name": "Eggs"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingredient["name"], user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredients(self):
        """Test creating a recipe with existing ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name="Lemon")
        payload = {
            "title": "Vietnamese Soup",
            "time_minutes": 25,
            "price": Decimal("2.50"),
            "ingredients": [{"name": "Lemon"}, {"name": "Fish Sauce"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())
        for ingredient in payload["ingredients"]:
            exists = recipe.ingredients.filter(
                name=ingredient["name"], user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe"""
        recipe = create_recipe(user=self.user)
        payload = {"ingredients": [{"name": "Limes"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name="Limes")
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe"""
        ingredient1 = Ingredient.objects.create(user=self.user, name="Pepper")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)
        ingredient2 = Ingredient.objects.create(user=self.user, name="Chili")
        payload = {"ingredients": [{"name": "Chili"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe's ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name="Garlic")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)
        payload = {"ingredients": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_filter_by_tags(self):
        """Test filtering recipes by tags."""
        r1 = create_recipe(user=self.user, title="Thai Vegetable Curry")
        r2 = create_recipe(user=self.user, title="Aubergine with Tahini")
        r3 = create_recipe(user=self.user, title="fish and chips")
        tag1 = Tag.objects.create(user=self.user, name="Vegan")
        tag2 = Tag.objects.create(user=self.user, name="Vegetarian")

        r1.tags.add(tag1)
        r2.tags.add(tag2)

        params = {"tags": f"{tag1.id},{tag2.id}"}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(user=self.user, title="Thai Vegetable Curry")
        r2 = create_recipe(user=self.user, title="Aubergine with Tahini")
        r3 = create_recipe(user=self.user, title="fish and chips")
        ingredient1 = Ingredient.objects.create(user=self.user, name="Feta cheese")
        ingredient2 = Ingredient.objects.create(user=self.user, name="Chicken")

        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)

        params = {"ingredients": f"{ingredient1.id},{ingredient2.id}"}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@example.com", password="password123")
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""

        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""

        url = image_upload_url(self.recipe.id)
        payload = {"image": "notanimage"}
        res = self.client.post(url, payload, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
