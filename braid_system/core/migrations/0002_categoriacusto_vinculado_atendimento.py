from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoriacusto',
            name='vinculado_atendimento',
            field=models.BooleanField(
                default=False,
                help_text='Indica que custos desta categoria costumam estar associados a um atendimento.',
            ),
        ),
    ]
