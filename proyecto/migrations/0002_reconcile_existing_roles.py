from django.db import migrations, models
import django.db.models.deletion


def ensure_role_schema(apps, schema_editor):
    """The existing MySQL database has these objects outside migration history.

    Adopt them without touching existing records or foreign keys, while also
    allowing migrations to build the same models in a fresh/test database.
    """
    Tipo = apps.get_model("proyecto", "Tipo")
    User = apps.get_model("proyecto", "User")
    with schema_editor.connection.cursor() as cursor:
        tables = schema_editor.connection.introspection.table_names(cursor)
    if Tipo._meta.db_table not in tables:
        schema_editor.create_model(Tipo)
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor, User._meta.db_table
        )
    if "tipo_id" not in {column.name for column in columns}:
        schema_editor.add_field(User, User._meta.get_field("tipo"))


class Migration(migrations.Migration):
    dependencies = [("proyecto", "0001_initial")]
    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name="Tipo",
                fields=[
                    ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                    ("nombre", models.CharField(max_length=50, unique=True)),
                ],
            ),
            migrations.AddField(
                model_name="user",
                name="tipo",
                field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="proyecto.tipo"),
            ),
        ]),
        # Never drop role data on reversal: these objects predate the migration.
        migrations.RunPython(ensure_role_schema, migrations.RunPython.noop, atomic=False),
    ]
