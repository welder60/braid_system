import uuid
from django.core.exceptions import ValidationError
from django.db import models


class CategoriaCusto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    ilustracao = models.CharField(max_length=500, blank=True)
    nivel_superior = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subcategorias',
        db_column='id_nivel_superior',
    )
    vinculado_atendimento = models.BooleanField(
        default=False,
        help_text='Indica que custos desta categoria costumam estar associados a um atendimento.',
    )

    class Meta:
        db_table = 'categoria_custo'
        verbose_name = 'Categoria de Custo'
        verbose_name_plural = 'Categorias de Custo'

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
    categoria_custo = models.ForeignKey(
        CategoriaCusto,
        on_delete=models.PROTECT,
        related_name='custos',
        db_column='id_categoria_custo',
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

    def clean(self):
        if self.categoria_custo_id and self.categoria_custo.nivel_superior_id is None:
            raise ValidationError(
                {'categoria_custo': (
                    'Não é permitido vincular uma super categoria a um custo.'
                    ' Selecione uma subcategoria.'
                )}
            )

    def __str__(self):
        return f'{self.categoria_custo} - {self.descricao}: R$ {self.valor}'
