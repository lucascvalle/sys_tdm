# core/models/items.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator

class ItemBase(models.Model):
    TIPO_ITEM = (
        ('PORT', 'Porta'),
        ('CABI', 'Armário'),
        ('PAVI', 'Pavimento'),
        ('COZI', 'Cozinha'),
        ('LAVA', 'Lavanderia')
    )
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    objeto_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'objeto_id')
    
    artigo = models.CharField(max_length=20, validators=[RegexValidator(r'^\d+(\.\d+)*$')])
    codigo_legado = models.CharField(max_length=50)
    descricao = models.TextField()
    preco_base = models.DecimalField(max_digits=10, decimal_places=2)
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class EstrategiaPrecificacao(models.Model):
    nome = models.CharField(max_length=50)
    formula = models.TextField()  # Armazena lógica em Python ou template string
    
    def __str__(self):
        return self.nome

class Item(ItemBase):
    tipo = models.CharField(max_length=4, choices=ItemBase.TIPO_ITEM)
    estrategia_preco = models.ForeignKey(EstrategiaPrecificacao, on_delete=models.PROTECT)
    atributos = models.JSONField(default=dict)
    
    def calcular_preco(self):
        # Implementação dinâmica baseada na estratégia
        return eval(self.estrategia_preco.formula, {'self': self})
    
    class Meta:
        ordering = ['artigo']

class ItemArvore(models.Model):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    ordem = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['ordere']
