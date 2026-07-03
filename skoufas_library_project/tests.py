"""Tests for top-level Skoufas Library project pages."""

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse


class ManualViewTests(TestCase):
    """Tests for the staff manual view."""

    def setUp(self):
        """Clear the manual render cache before each test."""
        cache.clear()

    def test_manual_is_reachable_without_login(self):
        """The manual page has no login gate, only the navbar link does."""
        response = self.client.get(reverse("manual"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Εγχειρίδιο Προσωπικού Βιβλιοθήκης Σκουφά")
        self.assertContains(response, "<h1")

    def test_manual_link_hidden_unless_logged_in(self):
        """The navbar only advertises the manual link to authenticated users."""
        anonymous_response = self.client.get(reverse("home"))
        self.assertNotContains(anonymous_response, reverse("manual"))

        user = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.client.force_login(user)
        logged_in_response = self.client.get(reverse("home"))
        self.assertContains(logged_in_response, reverse("manual"))
