import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_alter_atendimento_duracao_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FormaPagamento',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nome', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Forma de Pagamento',
                'verbose_name_plural': 'Formas de Pagamento',
                'db_table': 'forma_pagamento',
            },
        ),
        migrations.AddField(
            model_name='pagamento',
            name='forma_pagamento_fk',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagamentos',
                db_column='id_forma_pagamento',
                to='core.formapagamento',
            ),
        ),
        migrations.RunSQL(
            sql="""
                INSERT INTO forma_pagamento (id, nome)
                SELECT gen_random_uuid(), forma_pagamento
                FROM pagamento
                WHERE forma_pagamento IS NOT NULL AND forma_pagamento <> ''
                GROUP BY forma_pagamento;

                UPDATE pagamento p
                SET forma_pagamento_fk_id = fp.id
                FROM forma_pagamento fp
                WHERE p.forma_pagamento = fp.nome;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RemoveField(
            model_name='pagamento',
            name='forma_pagamento',
        ),
        migrations.RenameField(
            model_name='pagamento',
            old_name='forma_pagamento_fk',
            new_name='forma_pagamento',
        ),
        migrations.AlterField(
            model_name='pagamento',
            name='forma_pagamento',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='pagamentos',
                db_column='id_forma_pagamento',
                to='core.formapagamento',
            ),
        ),
    ]
