import uuid
from django.db import models


class Atendimento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estabelecimento = models.ForeignKey(
        'core.Estabelecimento',
        on_delete=models.PROTECT,
        related_name='atendimentos',
        db_column='id_estabelecimento',
    )
    cliente = models.ForeignKey(
        'core.Cliente',
        on_delete=models.PROTECT,
        related_name='atendimentos',
        db_column='id_cliente',
    )
    data = models.DateField()
    hora = models.TimeField()
    duracao = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duracao em minutos',
    )

    class Meta:
        db_table = 'atendimento'
        verbose_name = 'Atendimento'
        verbose_name_plural = 'Atendimentos'

    def __str__(self):
        return f'{self.estabelecimento} | {self.cliente} | {self.data} {self.hora}'


class Pagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    atendimento = models.ForeignKey(
        Atendimento,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        db_column='id_atendimento',
    )
    forma_pagamento = models.CharField(max_length=100, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'pagamento'
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'

    def __str__(self):
        return f'{self.atendimento} - {self.forma_pagamento}: R$ {self.valor}'
