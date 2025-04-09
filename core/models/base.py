from django.db import models
from mptt.models import MPTTModel, TreeForeignKey  # Usando django-mptt para hierarquia


class Item(MPTTModel):
    TIPOS_ITEM = (
        ('PORT', 'Porta'),
        ('CABI', 'Armário'),
    )

    codigo = models.CharField(max_length=20, unique=True)
    descricao = models.TextField()
    artigo = models.CharField(max_length=10)  # Ex: 1.1.1
    tipo = models.CharField(max_length=4, choices=TIPOS_ITEM)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    preco_base = models.DecimalField(max_digits=10, decimal_places=2)
    atributos = models.JSONField(default=dict)  # Para variações específicas

    class MPTTMeta:
        order_insertion_by = ['artigo']

    def __str__(self):
        return f"{self.artigo} - {self.descricao}"