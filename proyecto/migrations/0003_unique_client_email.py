from django.db import migrations, models
from django.db.models.functions import Lower, NullIf, Trim


def check_existing_emails(apps, schema_editor):
    if not schema_editor.connection.features.supports_expression_indexes:
        raise RuntimeError("This database must support expression indexes for safe email uniqueness.")
    User = apps.get_model("proyecto", "User")
    duplicates = (
        User.objects.using(schema_editor.connection.alias)
        .annotate(registration_email=NullIf(Lower(Trim("email")), models.Value("")))
        .exclude(registration_email__isnull=True)
        .values("registration_email")
        .annotate(total=models.Count("pk"))
        .filter(total__gt=1)
    )
    if duplicates.exists():
        # Stop instead of modifying, deleting, or disclosing existing accounts.
        raise RuntimeError("Duplicate nonblank emails exist. Resolve them before applying this migration; no accounts were changed.")


class Migration(migrations.Migration):
    dependencies = [("proyecto", "0002_reconcile_existing_roles")]
    operations = [
        migrations.RunPython(check_existing_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                NullIf(Lower(Trim("email")), models.Value("")),
                name="proyecto_user_email_ci_unique",
                violation_error_message="Este correo electrónico ya está registrado.",
            ),
        ),
    ]
