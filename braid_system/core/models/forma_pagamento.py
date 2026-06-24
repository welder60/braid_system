import uuid
from django.db import models


class FormaPagamento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=100)
    padrao = models.BooleanField(
        default=False,
        verbose_name='Padrão',
        help_text='Indica a forma de pagamento padrão. Apenas uma pode ser a padrão.',
    )

    class Meta:
        db_table = 'forma_pagamento'
        verbose_name = 'Forma de Pagamento'
        verbose_name_plural = 'Formas de Pagamento'
        constraints = [
            models.UniqueConstraint(
                fields=['padrao'],
                condition=models.Q(padrao=True),
                name='unique_forma_pagamento_padrao',
            ),
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        # Garante que apenas uma forma de pagamento seja a padrao:
        # ao marcar esta como padrao, as demais sao rebaixadas.
        if self.padrao:
            FormaPagamento.objects.exclude(pk=self.pk).filter(padrao=True).update(padrao=False)
        super().save(*args, **kwargs)
