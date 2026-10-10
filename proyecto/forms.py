from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import password_validators_help_text_html
from django.db.models.functions import Trim
from django.utils import translation

from .models import Tipo


class RegistroClienteForm(UserCreationForm):
    """Public registration only exposes identity fields, never permissions."""

    error_messages = {"password_mismatch": "Las contraseñas no coinciden."}

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("first_name", "last_name", "username", "email")
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "username": "Nombre de usuario",
            "email": "Correo electrónico",
        }
        error_messages = {
            "username": {
                "unique": "Este nombre de usuario ya está en uso.",
                "invalid": "Usa solo letras, números y los caracteres @ . + - _.",
            },
            "email": {"invalid": "Por favor, introduce un correo electrónico válido."},
        }

    def __init__(self, *args, **kwargs):
        with translation.override("es"):
            super().__init__(*args, **kwargs)
            self.fields["password1"].help_text = password_validators_help_text_html()
        self.fields["password1"].label = "Contraseña"
        self.fields["password2"].label = "Confirmar contraseña"
        self.fields["password2"].help_text = "Repite exactamente la misma contraseña."
        self.fields["username"].help_text = "Hasta 150 caracteres: letras, números y @ . + - _."
        placeholders = {
            "first_name": ("Ingresa tu nombre", "given-name"),
            "last_name": ("Ingresa tu apellido", "family-name"),
            "username": ("Elige un nombre de usuario", "username"),
            "email": ("nombre@ejemplo.com", "email"),
            "password1": ("Crea una contraseña segura", "new-password"),
            "password2": ("Repite tu contraseña", "new-password"),
        }
        for name, field in self.fields.items():
            field.required = True
            field.error_messages["required"] = f"Completa el campo {field.label.lower()}."
            field.widget.attrs.update({
                "class": "form-control",
                "placeholder": placeholders[name][0],
                "autocomplete": placeholders[name][1],
                "aria-describedby": f"id_{name}_help id_{name}_errors",
            })
            field.widget.attrs.pop("autofocus", None)
        self.fields["email"].widget.attrs.update({"autocapitalize": "none", "spellcheck": "false"})

    def full_clean(self):
        # Scope Spanish to this form; do not change the application's language.
        with translation.override("es"):
            return super().full_clean()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if self._meta.model.objects.annotate(
            registration_email=Trim("email")
        ).filter(registration_email__iexact=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Use the existing role by name, not a client-supplied value or a fixed ID.
        user.tipo = Tipo.objects.get(nombre="Cliente")
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            self.save_m2m()
        return user
