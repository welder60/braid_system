import uuid
from django.db import models


class TipoCusto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    ilustracao = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'tipo_custo'
        verbose_name = 'Tipo de Custo'
        verbose_name_plural = 'Tipos de Custo'

    def __str__(self):
        return self.nome


class Custo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estabelecimento = models.ForeignKey(
        'core.Estabelecimento',
        on_delete=models.PROTECT,
        related_name='custos',
        db_column='id_estabelecimento',
    )
    tipo_custo = models.ForeignKey(
        TipoCusto,
        on_delete=models.PROTECT,
        related_name='custos',
        db_column='id_tipo_custo',
    )
    atendimento = models.ForeignKey(
        'core.Atendimento',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='custos',
        db_column='id_atendimento',
    )
    descricao = models.CharField(max_length=255)
    data = models.DateField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'custo'
        verbose_name = 'Custo'
        verbose_name_plural = 'Custos'

    def __str__(self):
        return f'{self.tipo_custo} - {self.descricao}: R$ {self.valor}'
