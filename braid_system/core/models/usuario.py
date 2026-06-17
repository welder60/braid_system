import uuid
from django.db import models


class Usuario(models.Model):
    TIPO_CHOICES = [
        ('admin', 'Admin'),
        ('profissional', 'Profissional'),
        ('gerente', 'Gerente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    # LGPD Compliance
    termos_aceitos = models.BooleanField(default=False)
    data_consentimento = models.DateTimeField(null=True, blank=True)
    data_exclusao = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f'{self.nome} ({self.email})'
