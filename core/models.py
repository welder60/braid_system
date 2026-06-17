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
        'Usuario',
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


class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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


class Atendimento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    estabelecimento = models.ForeignKey(
        Estabelecimento,
        on_delete=models.PROTECT,
        related_name='atendimentos',
        db_column='id_estabelecimento',
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='atendimentos',
        db_column='id_cliente',
    )
    data = models.DateField()
    hora = models.TimeField()
    duracao = models.IntegerField(help_text='Duracao em minutos')

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
    forma_pagamento = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'pagamento'
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'

    def __str__(self):
        return f'{self.atendimento} - {self.forma_pagamento}: R$ {self.valor}'


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
        Atendimento,
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
    tipo_custo = models.ForeignKey(
        TipoCusto,
        on_delete=models.PROTECT,
        related_name='custos',
        db_column='id_tipo_custo',
    )
    atendimento = models.ForeignKey(
        Atendimento,
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
