# Generated by Django 5.2.4 on 2025-07-15 15:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('produtos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Orcamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_legado', models.CharField(max_length=100, unique=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('versao', models.PositiveIntegerField(default=1)),
                ('versao_base', models.PositiveIntegerField(default=1, help_text='Indica a versão do orçamento que serviu de base (para versões >1)')),
                ('nome_cliente', models.CharField(blank=True, max_length=255, null=True)),
                ('tipo_cliente', models.CharField(blank=True, max_length=10, null=True)),
                ('codigo_cliente', models.CharField(blank=True, max_length=50, null=True)),
                ('data_solicitacao', models.DateField(blank=True, null=True)),
                ('codigo_agente', models.CharField(blank=True, max_length=50, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ItemOrcamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preco_unitario', models.DecimalField(decimal_places=2, max_digits=12)),
                ('quantidade', models.PositiveIntegerField()),
                ('total', models.DecimalField(decimal_places=2, max_digits=14)),
                ('instancia', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='produtos.produtoinstancia')),
                ('orcamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='orcamentos.orcamento')),
            ],
        ),
        migrations.AddConstraint(
            model_name='orcamento',
            constraint=models.UniqueConstraint(fields=('codigo_legado', 'versao'), name='unique_codigo_versao'),
        ),
    ]
