import uuid
import django.db.models.deletion  # used by AddField
from django.db import migrations, models


def copiar_formas_pagamento(apps, schema_editor):
    """Migra os valores textuais de forma_pagamento para a nova tabela FormaPagamento.

    Versao portavel (RunPython) que substitui o SQL especifico de PostgreSQL,
    funcionando tambem em SQLite (usado em dev/testes).
    """
    Pagamento = apps.get_model("core", "Pagamento")
    FormaPagamento = apps.get_model("core", "FormaPagamento")

    formas_por_nome = {}
    for pagamento in Pagamento.objects.all():
        nome = (getattr(pagamento, "forma_pagamento", "") or "").strip()
        if not nome:
            continue
        forma = formas_por_nome.get(nome)
        if forma is None:
            forma, _ = FormaPagamento.objects.get_or_create(nome=nome)
            formas_por_nome[nome] = forma
        pagamento.forma_pagamento_fk = forma
        pagamento.save(update_fields=["forma_pagamento_fk"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_atendimento_duracao_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormaPagamento",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("nome", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name": "Forma de Pagamento",
                "verbose_name_plural": "Formas de Pagamento",
                "db_table": "forma_pagamento",
            },
        ),
        migrations.AddField(
            model_name="pagamento",
            name="forma_pagamento_fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pagamentos",
                db_column="id_forma_pagamento",
                to="core.formapagamento",
            ),
        ),
        migrations.RunPython(
            copiar_formas_pagamento,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="pagamento",
            name="forma_pagamento",
        ),
        migrations.RenameField(
            model_name="pagamento",
            old_name="forma_pagamento_fk",
            new_name="forma_pagamento",
        ),
    ]
