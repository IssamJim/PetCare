from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.functions import Lower, NullIf, Trim

# Create your models here.

class Tipo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nombre
    
class User(AbstractUser):
    tipo = models.ForeignKey('proyecto.Tipo', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                NullIf(Lower(Trim('email')), models.Value('')),
                name='proyecto_user_email_ci_unique',
                violation_error_message='Este correo electrónico ya está registrado.',
            ),
        ]

    def __str__(self):
        return f"{self.username} - {self.tipo.nombre if self.tipo else 'Sin Rol'}"
