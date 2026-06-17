import uuid
from django.db import models


class Estabelecimento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)

    class Meta:
        db_table = 'estabelecimento'
        verbose_name = 'Estabelecimento'
        verbose_name_plural = 'Estabelecimentos'

    def __str__(self):
        return self.nome


class EstabelecimentoUsuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.CASCADE,
        related_name='estabelecimento_usuarios',
        db_column='id_estabelecimento',
    )
    usuario = models.ForeignKey(
        'security.Usuario',
        on_delete=models.CASCADE,
        related_name='estabelecimento_usuarios',
        db_column='id_usuario',
    )

    class Meta:
        db_table = 'estabelecimento_usuario'
        verbose_name = 'Estabelecimento Usuario'
        verbose_name_plural = 'Estabelecimentos Usuarios'
        unique_together = ('estabelecimento', 'usuario')

    def __str__(self):
        return f'{self.estabelecimento} - {self.usuario}'
