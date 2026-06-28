import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_formapagamento_alter_pagamento_forma_pagamento"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pagamento",
            name="forma_pagamento",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pagamentos",
                db_column="id_forma_pagamento",
                to="core.formapagamento",
            ),
        ),
    ]
