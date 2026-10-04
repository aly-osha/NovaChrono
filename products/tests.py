from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from products.models import Game, Set


class AdminGameSetManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="admin_gameset",
            email="admin_gameset@example.com",
            password="securePassword123!",
            role="admin",
        )
        self.client.force_login(self.admin_user)

    def test_admin_create_game_standard_post(self):
        url = reverse("admin_game_create")
        response = self.client.post(url, {"name": "Lorcana TCG", "description": "Disney trading card game"})
        self.assertEqual(response.status_code, 302)
        game = Game.objects.filter(name="Lorcana TCG").first()
        self.assertIsNotNone(game)
        self.assertEqual(game.description, "Disney trading card game")
        self.assertTrue(game.is_active)

    def test_admin_create_game_ajax_post(self):
        url = reverse("admin_game_create")
        response = self.client.post(
            url,
            {"name": "One Piece TCG", "description": "Bandai card game", "is_ajax": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(Game.objects.filter(name="One Piece TCG").exists())

    def test_admin_create_set_standard_post(self):
        game = Game.objects.create(name="Pokemon Test")
        url = reverse("admin_set_create")
        response = self.client.post(url, {"game": game.pk, "name": "Surging Sparks", "code": "SSP"})
        self.assertEqual(response.status_code, 302)
        s = Set.objects.filter(name="Surging Sparks", game=game).first()
        self.assertIsNotNone(s)
        self.assertEqual(s.code, "SSP")
        self.assertTrue(s.is_active)

    def test_admin_create_set_ajax_post(self):
        game = Game.objects.create(name="Magic Test")
        url = reverse("admin_set_create")
        response = self.client.post(
            url,
            {"game": game.pk, "name": "Modern Horizons 3", "code": "MH3", "is_ajax": "1"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(Set.objects.filter(name="Modern Horizons 3", game=game).exists())

