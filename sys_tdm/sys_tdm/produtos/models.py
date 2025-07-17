from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Atributo(models.Model):
    TIPO_CHOICES = [
        ('num', 'Numérico'),
        ('str', 'Texto'),
        ('choice', 'Escolha'),
    ]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    def __str__(self):
        return self.nome

class ItemMaterial(models.Model):
    descricao = models.CharField(max_length=200)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    unidade = models.CharField(max_length=20)

    def __str__(self):
        return self.descricao

class ProdutoTemplate(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='templates')
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    unidade = models.CharField(max_length=50, blank=True, null=True, help_text="Unidade de medida do produto (ex: m², unidade, kg)")

    def __str__(self):
        return f"{self.categoria.nome} - {self.nome}"

class TemplateAtributo(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='atributos')
    atributo = models.ForeignKey(Atributo, on_delete=models.PROTECT)
    obrigatorio = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)

    class Meta:
        unique_together = ('template', 'atributo')

class TemplateComponente(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='componentes')
    item_material = models.ForeignKey(ItemMaterial, on_delete=models.PROTECT)
    quantidade_expr = models.CharField(max_length=100,
        help_text='Use expressões em Python com atributos do template, ex: (altura+largura)*2')
    unidade = models.CharField(max_length=20)
    fator_perda = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('template', 'item_material')

class FormulaTemplate(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.CASCADE, related_name='formulas')
    expressao = models.TextField(
        help_text='Expressão global de cálculo, ex: sum(mat)+sum(mod)*1.2+overhead')

# Instâncias para orçamentos
class ProdutoInstancia(models.Model):
    template = models.ForeignKey(ProdutoTemplate, on_delete=models.PROTECT, related_name='instancias')
    codigo = models.CharField(max_length=50)
    quantidade = models.PositiveIntegerField(default=1)

class InstanciaAtributo(models.Model):
    instancia = models.ForeignKey(ProdutoInstancia, on_delete=models.CASCADE, related_name='atributos')
    atributo = models.ForeignKey(Atributo, on_delete=models.PROTECT)
    valor_texto = models.CharField(max_length=200, blank=True)
    valor_num = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    class Meta:
        unique_together = ('instancia', 'atributo')

class InstanciaComponente(models.Model):
    instancia = models.ForeignKey(ProdutoInstancia, on_delete=models.CASCADE, related_name='componentes')
    item_material = models.ForeignKey(ItemMaterial, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=4)
    unidade = models.CharField(max_length=20)
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2)