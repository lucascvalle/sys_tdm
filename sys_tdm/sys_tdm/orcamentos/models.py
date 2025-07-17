from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Orcamento(models.Model):
    codigo_legado = models.CharField(max_length=100, unique=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    versao = models.PositiveIntegerField(default=1)
    versao_base = models.PositiveIntegerField(default=1,
        help_text='Indica a versão do orçamento que serviu de base (para versões >1)')

    # Novos campos para armazenar dados extraídos do codigo_legado
    nome_cliente = models.CharField(max_length=255, blank=True, null=True)
    tipo_cliente = models.CharField(max_length=10, blank=True, null=True) # Ex: 'EP' ou 'PC'
    codigo_cliente = models.CharField(max_length=50, blank=True, null=True)
    data_solicitacao = models.DateField(blank=True, null=True)
    codigo_agente = models.CharField(max_length=50, blank=True, null=True) # Ex: '80-ELLA'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['codigo_legado', 'versao'], name='unique_codigo_versao')
        ]

    def __str__(self):
        return f"Orçamento {self.codigo_legado} v{self.versao}"

class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    codigo_item_manual = models.CharField(max_length=50, blank=True, null=True, help_text="Código manual do item no orçamento (ex: P01)")
    instancia = models.ForeignKey('produtos.ProdutoInstancia', on_delete=models.PROTECT)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=14, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)