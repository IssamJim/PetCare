"""Optional real-browser verification against Django's disposable test database."""
import os
from pathlib import Path
import subprocess
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings

from .models import Tipo


@skipUnless(os.environ.get("PETCARE_BROWSER_TESTS") == "1", "Set PETCARE_BROWSER_TESTS=1 with Playwright installed.")
@override_settings(DEBUG=False)
class RegistrationBrowserTests(StaticLiveServerTestCase):
    def test_desktop_mobile_validation_registration_and_login(self):
        Tipo.objects.create(nombre="Cliente")
        root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            ["node", str(root / "tests" / "registration_browser.cjs"), self.live_server_url],
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(get_user_model().objects.count(), 1)
        user = get_user_model().objects.get(username="browser_client")
        self.assertEqual(user.tipo.nombre, "Cliente")
        self.assertFalse(user.is_staff or user.is_superuser)
