from django.db import models
from django.contrib.auth import get_user_model
from produtos.models import ProdutoInstancia, ProdutoConfiguracao

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
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    codigo_item_manual = models.CharField(max_length=50, blank=True, null=True, help_text="Código manual do item no orçamento (ex: P01)")
    
    # Relacionamento com a configuração do produto, que é mais geral
    configuracao = models.ForeignKey(ProdutoConfiguracao, on_delete=models.PROTECT, null=True, blank=True)
    
    # Relacionamento com a instância específica do produto (pode ser nulo para itens de template)
    instancia = models.ForeignKey(ProdutoInstancia, on_delete=models.PROTECT, null=True, blank=True)
    
    # Campos para informações de preço e quantidade
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade = models.PositiveIntegerField()
    margem_negocio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.0)
    total = models.DecimalField(max_digits=14, decimal_places=2)

    def save(self, *args, **kwargs):
        # O cálculo do total pode precisar de lógica mais complexa
        # dependendo se é um item pai ou filho.
        self.total = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)

    def __str__(self):
        if self.instancia:
            return f"Item: {self.instancia.codigo} - {self.instancia.configuracao.nome}"
        elif self.configuracao:
            return f"Configuração: {self.configuracao.nome}"
        else:
            return f"Item de Orçamento {self.id}"