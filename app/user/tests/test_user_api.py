"""Tests for the user API"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


CREATE_USER_URL = reverse("user:register")
LOGIN_URL = reverse("user:login")
ME_URL = reverse("user:me")


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the public features of the user api."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""

        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name",
        }  # test payload
        res = self.client.post(CREATE_USER_URL, payload)  # call api
        self.assertEqual(
            res.status_code, status.HTTP_201_CREATED
        )  # check if res status = 201 (successful)

        user = get_user_model().objects.get(
            email=payload["email"]
        )  # check if user is add to the database
        self.assertTrue(
            user.check_password(payload["password"])
        )  # check if the password is set correctly
        self.assertNotIn("password", res.data)

    def test_user_with_email_exists_error(self):
        """Test error returned if user with same email exists"""

        payload = {
            "email": "test@example.com",
            "password": "testpass123",
            "name": "Test Name",
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test an error is returned if password less than 5 chars."""

        payload = {
            "email": "test@example.com",
            "password": "pw",
            "name": "Test Name",
        }

        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(email=payload["email"]).exists()
        self.assertFalse(user_exists)

    def test_login_user(self):
        """Test generates token when logged in"""

        user = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "testpass123",
        }
        create_user(**user)

        payload = {"email": user["email"], "password": user["password"]}
        res = self.client.post(LOGIN_URL, payload)

        self.assertIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_login_bad_credentials(self):
        """Test return error if credentials invalid"""
        user = {
            "name": "Test Name",
            "email": "test@example.com",
            "password": "correctpass123",
        }
        create_user(**user)

        test_cases = [
            {
                "payload": {"email": "wrong@example.com", "password": "correctpass123"},
                "message": "Invalid email",
            },
            {
                "payload": {"email": "test@example.com", "password": "wrongpass123"},
                "message": "Invalid password",
            },
            {
                "payload": {"email": "test@example.com", "password": ""},
                "message": "Password Must Not Be Empty",
            },
        ]

        for test_case in test_cases:
            with self.subTest(msg=test_case["message"]):
                res = self.client.post(LOGIN_URL, test_case["payload"])

                self.assertNotIn("token", res.data)
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        """Test authentication is required for users."""

        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateUserApiTests(TestCase):
    """Test API requests the require authentication"""

    def setUp(self):
        self.user = create_user(
            email="test@example.com", password="testpass123", name="Test User"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """Test retrieving profile for logged in user."""

        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {"email": self.user.email, "name": self.user.name})

    def test_post_me_not_allowed(self):
        """Test POST is not allowed for me endpoint"""

        res = self.client.post(ME_URL, {})
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """Test updating user profile"""

        payload = {"name": "UpdatedName", "password": "newpassword123"}
        res = self.client.patch(ME_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()

        self.assertEqual(self.user.name, payload["name"])
        self.assertTrue(self.user.check_password(payload["password"]))
