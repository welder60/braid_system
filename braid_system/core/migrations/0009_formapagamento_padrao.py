from django.db import migrations, models


FORMAS_PADRAO = [
    ('PIX', True),
    ('Débito', False),
    ('Crédito', False),
    ('Dinheiro', False),
]


def seed_formas_pagamento(apps, schema_editor):
    """Cria as formas de pagamento padrao do sistema.

    PIX e definida como a forma de pagamento padrao. As demais formas
    existentes (se houver) sao rebaixadas para garantir uma unica padrao.
    """
    FormaPagamento = apps.get_model('core', 'FormaPagamento')

    # Garante que nenhuma forma pre-existente fique marcada como padrao
    # antes de definirmos a nova padrao (respeita a constraint unica).
    FormaPagamento.objects.filter(padrao=True).update(padrao=False)

    for nome, padrao in FORMAS_PADRAO:
        forma, _ = FormaPagamento.objects.get_or_create(nome=nome)
        if forma.padrao != padrao:
            forma.padrao = padrao
            forma.save(update_fields=['padrao'])


def unseed_formas_pagamento(apps, schema_editor):
    """Apenas remove a marcacao de padrao na reversao.

    Nao deletamos as formas para evitar violar a PROTECT de Pagamento.
    """
    FormaPagamento = apps.get_model('core', 'FormaPagamento')
    FormaPagamento.objects.filter(padrao=True).update(padrao=False)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_pagamento_forma_pagamento_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='formapagamento',
            name='padrao',
            field=models.BooleanField(
                default=False,
                help_text='Indica a forma de pagamento padrão. Apenas uma pode ser a padrão.',
                verbose_name='Padrão',
            ),
        ),
        migrations.RunPython(
            seed_formas_pagamento,
            reverse_code=unseed_formas_pagamento,
        ),
        migrations.AddConstraint(
            model_name='formapagamento',
            constraint=models.UniqueConstraint(
                fields=['padrao'],
                condition=models.Q(padrao=True),
                name='unique_forma_pagamento_padrao',
            ),
        ),
    ]
