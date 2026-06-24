import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nome, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, nome=nome, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nome, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo', 'admin')
        return self.create_user(email, nome, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    TIPO_CHOICES = [
        ('admin', 'Admin'),
        ('profissional', 'Profissional'),
        ('gerente', 'Gerente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES)
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    # LGPD Compliance
    termos_aceitos = models.BooleanField(default=False)
    data_consentimento = models.DateTimeField(null=True, blank=True)
    data_exclusao = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='core_usuario_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='core_usuario_set',
        blank=True,
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f'{self.nome} ({self.email})'

    @property
    def is_active(self):
        return self.ativo

    @property
    def is_admin_role(self):
        """Papéis com acesso à área de administração (admin ou consultor)."""
        return self.tipo in ('admin', 'consultor')
