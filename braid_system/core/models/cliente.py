import uuid
from django.db import models


class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estabelecimento = models.ForeignKey(
        'core.Estabelecimento',
        on_delete=models.PROTECT,
        related_name='clientes',
        db_column='id_estabelecimento',
    )
    apelido = models.CharField(max_length=255, blank=True)
    descricao = models.TextField(blank=True)
    # LGPD Compliance
    consentimento_dados_sensiveis = models.BooleanField(default=False)
    anonimizado = models.BooleanField(default=False)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.apelido or str(self.id)
