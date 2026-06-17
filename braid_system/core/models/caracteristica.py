import uuid
from django.db import models


class CaracteristicaAtendimento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ordem = models.IntegerField()
    nome = models.CharField(max_length=255)
    pergunta = models.TextField()
    numero_maximo_selecao = models.IntegerField(default=1)
    # LGPD Compliance
    contem_dado_sensivel = models.BooleanField(
        default=False,
        help_text='Sinaliza se a pergunta exige governanca estrita (ex: alergias)',
    )

    class Meta:
        db_table = 'caracteristica_atendimento'
        verbose_name = 'Caracteristica de Atendimento'
        verbose_name_plural = 'Caracteristicas de Atendimento'
        ordering = ['ordem']

    def __str__(self):
        return self.nome


class CaracteristicaAtendimentoOpcao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    caracteristica_atendimento = models.ForeignKey(
        CaracteristicaAtendimento,
        on_delete=models.CASCADE,
        related_name='opcoes',
        db_column='id_caracteristica_atendimento',
    )
    nivel_superior = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subdivisoes',
        db_column='id_nivel_superior',
    )
    nome = models.CharField(max_length=255)
    ilustracao = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'caracteristica_atendimento_opcao'
        verbose_name = 'Opcao de Caracteristica de Atendimento'
        verbose_name_plural = 'Opcoes de Caracteristica de Atendimento'

    def __str__(self):
        return f'{self.caracteristica_atendimento} - {self.nome}'


class AtendimentoCaracteristica(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    atendimento = models.ForeignKey(
        'core.Atendimento',
        on_delete=models.CASCADE,
        related_name='caracteristicas',
        db_column='id_atendimento',
    )
    opcao = models.ForeignKey(
        CaracteristicaAtendimentoOpcao,
        on_delete=models.PROTECT,
        related_name='atendimento_caracteristicas',
        db_column='id_caracteristica_atendimento_opcao',
    )

    class Meta:
        db_table = 'atendimento_caracteristica'
        verbose_name = 'Caracteristica do Atendimento'
        verbose_name_plural = 'Caracteristicas do Atendimento'
        unique_together = ('atendimento', 'opcao')

    def __str__(self):
        return f'{self.atendimento} - {self.opcao}'
