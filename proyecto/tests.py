from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import authenticate, get_user_model
from django.db import DatabaseError, IntegrityError, close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import translation

from .forms import RegistroClienteForm
from .models import Tipo

User = get_user_model()
TEST_PASSWORD = "Luna!Montana-4729"


def registration_data(**changes):
    data = {
        "first_name": "María",
        "last_name": "García",
        "username": "maria_cliente",
        "email": "maria@example.com",
        "password1": TEST_PASSWORD,
        "password2": TEST_PASSWORD,
    }
    data.update(changes)
    return data


@override_settings(DEBUG=False)
class RegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client_role = Tipo.objects.create(nombre="Cliente")
        cls.admin_role = Tipo.objects.create(nombre="Administrador")

    def post(self, **changes):
        return self.client.post(reverse("registro_cliente"), registration_data(**changes))

    def test_login_link_and_spanish_form(self):
        login = self.client.get(reverse("custom_login"))
        self.assertContains(login, 'href="/registro/">Regístrate</a>')
        response = self.client.get(reverse("registro_cliente"))
        for text in ('lang="es"', "Nombre de usuario", "Confirmar contraseña", 'type="email"', 'csrfmiddlewaretoken'):
            self.assertContains(response, text)
        self.assertNotContains(response, 'name="tipo"')
        self.assertContains(response, "Su contraseña")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_success_hashes_password_sets_client_role_and_existing_login_works(self):
        response = self.post()
        self.assertRedirects(response, reverse("registro_exitoso"), fetch_redirect_response=False)
        user = User.objects.get(username="maria_cliente")
        self.assertEqual(user.tipo, self.client_role)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.groups.count(), 0)
        self.assertEqual(user.user_permissions.count(), 0)
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertEqual(authenticate(username=user.username, password=TEST_PASSWORD), user)
        self.assertNotIn("_auth_user_id", self.client.session)
        success = self.client.get(response.url)
        self.assertContains(success, "¡Registro exitoso!")
        self.assertContains(success, "Tu cuenta ha sido creada correctamente.")
        self.assertContains(success, "Iniciar sesión")
        login = self.client.post(reverse("custom_login"), {"username": user.username, "password": TEST_PASSWORD})
        self.assertRedirects(login, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_trims_identity_fields_but_not_passwords(self):
        password = "  Bosque!Roca-90821  "
        self.post(first_name="  Ana  ", last_name="  López  ", username="  ana_l  ",
                  email="  ANA@Example.COM  ", password1=password, password2=password)
        user = User.objects.get(username="ana_l")
        self.assertEqual((user.first_name, user.last_name, user.email), ("Ana", "López", "ana@example.com"))
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.check_password(password.strip()))

    def test_all_required_fields_have_spanish_errors_and_no_account(self):
        for name in registration_data():
            with self.subTest(field=name):
                response = self.post(**{name: ""})
                self.assertIn(name, response.context["form"].errors)
                self.assertContains(response, "Completa el campo")
                self.assertContains(response, 'id="registration-errors"')
                self.assertContains(response, 'aria-invalid="true"')
        self.assertEqual(User.objects.count(), 0)
        response = self.client.post(reverse("registro_cliente"), {})
        self.assertEqual(len(response.context["form"].errors), 6)

    def test_invalid_email_and_username_rules(self):
        for email in ("invalid", "one@@example.com", "a@", " "):
            with self.subTest(email=email):
                self.assertIn("email", self.post(email=email).context["form"].errors)
        self.assertContains(self.post(email="wrong"), "Por favor, introduce un correo electrónico válido.")
        response = self.post(username="invalid name!")
        self.assertIn("username", response.context["form"].errors)
        self.assertContains(response, "Usa solo letras")
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_username_uses_existing_case_insensitive_behavior(self):
        User.objects.create_user(username="MARIA_CLIENTE", password=TEST_PASSWORD, tipo=self.client_role)
        response = self.post()
        self.assertContains(response, "Este nombre de usuario ya está en uso.")
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_duplicate_email_is_case_insensitive_and_trims_legacy_email(self):
        User.objects.create_user(username="existing", email=" Maria@Example.com ", tipo=self.client_role)
        response = self.post()
        self.assertContains(response, "Este correo electrónico ya está registrado.")
        self.assertIn("email", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_password_mismatch_and_configured_validators(self):
        response = self.post(password2=TEST_PASSWORD + " ")
        self.assertContains(response, "Las contraseñas no coinciden.")
        for password in ("123", "password", "12345678912345", "maria_cliente"):
            with self.subTest(password_case=len(password)):
                response = self.post(password1=password, password2=password)
                self.assertIn("password2", response.context["form"].errors)
                self.assertNotContains(response, "This password")
        self.assertEqual(User.objects.count(), 0)

    def test_nonpassword_values_preserved_passwords_not_redisplayed(self):
        response = self.post(email="bad-email")
        self.assertContains(response, 'value="María"')
        self.assertContains(response, 'value="bad-email"')
        self.assertNotContains(response, TEST_PASSWORD)

    def test_invalid_submission_escapes_untrusted_values(self):
        response = self.post(first_name='<img src=x onerror="alert(1)">', email="bad-email")
        self.assertNotContains(response, '<img src=x onerror=')
        self.assertContains(response, '&lt;img src=x onerror=')
        self.assertEqual(User.objects.count(), 0)

    def test_permission_injection_is_ignored(self):
        response = self.post(tipo=self.admin_role.pk, rol=self.admin_role.pk, role="Administrador",
                             is_staff="1", is_superuser="1", groups="1", user_permissions="1")
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="maria_cliente")
        self.assertEqual(user.tipo, self.client_role)
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertFalse(user.groups.exists() or user.user_permissions.exists())

    def test_duplicate_submission_creates_one_account(self):
        self.assertEqual(self.post().status_code, 302)
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        self.assertIn("username", response.context["form"].errors)
        self.assertIn("email", response.context["form"].errors)

    def test_success_page_requires_completed_registration_and_refresh_cannot_resubmit(self):
        self.assertRedirects(self.client.get(reverse("registro_exitoso")), reverse("registro_cliente"))
        self.post()
        self.assertEqual(self.client.get(reverse("registro_exitoso")).status_code, 200)
        self.assertRedirects(self.client.get(reverse("registro_exitoso")), reverse("registro_cliente"))
        self.assertEqual(User.objects.count(), 1)

    def test_missing_client_role_fails_closed_without_creating_accounts(self):
        self.client_role.delete()
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, "El registro de clientes no está disponible", status_code=503)
        self.assertEqual(User.objects.count(), 0)

    def test_transaction_rolls_back_partial_save_and_hides_database_details(self):
        original_save = RegistroClienteForm.save

        def fail_after_save(form, *args, **kwargs):
            original_save(form, *args, **kwargs)
            raise IntegrityError("internal database details")

        with patch.object(RegistroClienteForm, "save", fail_after_save):
            response = self.post()
        self.assertEqual(User.objects.count(), 0)
        self.assertContains(response, "No se pudo completar el registro")
        self.assertNotContains(response, "internal database details")
        self.assertNotContains(response, TEST_PASSWORD)

    def test_database_outage_returns_spanish_error(self):
        with patch.object(RegistroClienteForm, "clean_email", side_effect=DatabaseError("private failure")):
            response = self.post()
        self.assertContains(response, "Inténtalo más tarde.", status_code=503)
        self.assertNotContains(response, "private failure", status_code=503)
        self.assertEqual(User.objects.count(), 0)

    def test_csrf_is_required_and_valid_token_is_accepted(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("registro_cliente"), registration_data()).status_code, 403)
        client.get(reverse("registro_cliente"))
        response = client.post(reverse("registro_cliente"), {
            **registration_data(), "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.count(), 1)

    def test_only_get_and_post_are_accepted(self):
        self.assertEqual(self.client.put(reverse("registro_cliente")).status_code, 405)
        self.assertEqual(self.client.post(reverse("registro_exitoso")).status_code, 405)

    def test_database_constraint_blocks_duplicate_nonblank_email(self):
        User.objects.create_user(username="one", email="Mixed@Example.com", tipo=self.client_role)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username="two", email=" mixed@example.COM ", tipo=self.client_role)
        self.assertEqual(User.objects.count(), 1)

    def test_existing_blank_emails_remain_supported(self):
        User.objects.create_user(username="legacy_one", email="", tipo=self.admin_role)
        User.objects.create_user(username="legacy_two", email="", tipo=self.admin_role)
        self.assertEqual(User.objects.count(), 2)

    def test_clients_cannot_use_existing_account_management_to_escalate(self):
        self.post()
        user = User.objects.get(username="maria_cliente")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("vista_usuario")).status_code, 403)
        response = self.client.post(reverse("crear_usuario"), {
            "nombre": "Forbidden", "apellido": "Account", "username": "escalated",
            "password": TEST_PASSWORD, "rol": self.admin_role.pk,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="escalated").exists())

    def test_existing_administrator_login_and_creation_still_work(self):
        admin = User.objects.create_user(username="existing_admin", password=TEST_PASSWORD, tipo=self.admin_role)
        response = self.client.post(reverse("custom_login"), {"username": admin.username, "password": TEST_PASSWORD})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.get(reverse("vista_usuario")).status_code, 200)
        response = self.client.post(reverse("crear_usuario"), {
            "nombre": "Staff", "apellido": "Account", "username": "managed_account",
            "password": TEST_PASSWORD, "rol": self.admin_role.pk,
        })
        self.assertRedirects(response, reverse("vista_usuario"))
        self.assertEqual(User.objects.get(username="managed_account").tipo, self.admin_role)

    def test_form_messages_are_spanish_without_changing_global_language(self):
        with translation.override("en"):
            form = RegistroClienteForm(registration_data(password1="123", password2="123"))
            self.assertFalse(form.is_valid())
            self.assertNotIn("This password", str(form.errors))
            self.assertEqual(translation.get_language(), "en")


@skipUnless(connection.vendor == "mysql", "Concurrency must be verified against MySQL.")
@override_settings(DEBUG=False)
class RegistrationConcurrencyTests(TransactionTestCase):
    def concurrent_registration(self, same_username=False):
        Tipo.objects.create(nombre="Cliente")
        barrier = Barrier(2)
        original_save = RegistroClienteForm.save

        def synchronized_save(form, *args, **kwargs):
            barrier.wait(timeout=15)
            return original_save(form, *args, **kwargs)

        def submit(index):
            close_old_connections()
            try:
                response = Client().post(reverse("registro_cliente"), registration_data(
                    username="same_username" if same_username else f"concurrent_{index}",
                    email=f"different{index}@example.com" if same_username else (
                        "SAME@example.com" if index == 0 else "same@EXAMPLE.com"
                    ),
                ))
                return response.status_code, response.content.decode()
            finally:
                connection.close()

        with patch.object(RegistroClienteForm, "save", synchronized_save):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(submit, range(2)))
        self.assertEqual(sorted(status for status, _ in results), [200, 302])
        self.assertEqual(User.objects.count(), 1)
        rejected = next(body for status, body in results if status == 200)
        return rejected

    def test_concurrent_registration_for_same_email_creates_one_account(self):
        rejected = self.concurrent_registration()
        self.assertIn("Este correo electrónico ya está registrado.", rejected)

    def test_concurrent_registration_for_same_username_creates_one_account(self):
        rejected = self.concurrent_registration(same_username=True)
        self.assertIn("Este nombre de usuario ya está en uso.", rejected)
