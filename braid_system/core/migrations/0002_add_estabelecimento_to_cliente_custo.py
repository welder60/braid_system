import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='estabelecimento',
            field=models.ForeignKey(
                db_column='id_estabelecimento',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='clientes',
                to='core.estabelecimento',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='custo',
            name='estabelecimento',
            field=models.ForeignKey(
                db_column='id_estabelecimento',
                on_delete=django.db.models.deletion.PROTECT,
                related_name='custos',
                to='core.estabelecimento',
            ),
            preserve_default=False,
        ),
    ]
