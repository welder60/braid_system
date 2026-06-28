# Adiciona o tipo "Consultor" às opções de Usuario.tipo.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("security", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usuario",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("profissional", "Profissional"),
                    ("gerente", "Gerente"),
                    ("consultor", "Consultor"),
                ],
                max_length=50,
            ),
        ),
    ]
