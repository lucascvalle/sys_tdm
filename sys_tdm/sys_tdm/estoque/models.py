from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

class CategoriaItem(models.Model):
    """
    Categorias hierárquicas para os itens de estoque.
    Ex: Matéria-Prima > Painéis > MDF
    """
    nome = models.CharField(max_length=100, help_text="Ex: Ferragens, Painéis de Madeira, Consumíveis")
    codigo_categoria = models.CharField(max_length=10, unique=True, help_text="Prefixo único para esta categoria (ex: FER, PNL, QMC).", null=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategorias')

    class Meta:
        verbose_name = "Categoria de Item"
        verbose_name_plural = "Categorias de Itens"
        unique_together = ('nome', 'parent')

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.nome}"
        return self.nome

class ItemEstocavel(models.Model):
    """
    Representa um item físico e comprável que existe em estoque. O "Produto Simples".
    """
    UNIDADE_CHOICES = [
        ('un', 'Unidade'),
        ('m', 'Metro Linear'),
        ('m2', 'Metro Quadrado'),
        ('m3', 'Metro Cúbico'),
        ('kg', 'Quilograma'),
        ('L', 'Litro'),
    ]

    categoria = models.ForeignKey(CategoriaItem, on_delete=models.PROTECT, related_name='itens')
    nome = models.CharField(max_length=255, help_text="Ex: Painel MDF Hidrófugo 19mm 2440x1220")
    descricao = models.TextField(blank=True, help_text="Detalhes técnicos, fornecedor, etc.")
    
    # Código do Fornecedor
    codigo_sku_fornecedor = models.CharField(max_length=100, blank=True, help_text="SKU (Stock Keeping Unit) ou código de barras do fornecedor.")

    # Código Interno Gerado Automaticamente
    codigo_interno_item = models.PositiveIntegerField(editable=False, help_text="Código sequencial do item dentro da categoria.", null=True)
    codigo_interno_gerado = models.CharField(max_length=20, unique=True, editable=False, help_text="Código interno completo gerado automaticamente (ex: PNL-0001).", null=True)

    unidade_medida = models.CharField(max_length=5, choices=UNIDADE_CHOICES, default='un')

    # Campos dimensionais para facilitar cálculos
    largura_mm = models.PositiveIntegerField(null=True, blank=True, help_text="Largura em milímetros")
    altura_mm = models.PositiveIntegerField(null=True, blank=True, help_text="Altura ou comprimento em milímetros")
    espessura_mm = models.PositiveIntegerField(null=True, blank=True, help_text="Espessura em milímetros")

    class Meta:
        verbose_name = "Item Estocável"
        verbose_name_plural = "Itens Estocáveis"
        unique_together = ('categoria', 'codigo_interno_item')

    def __str__(self):
        return f"{self.nome} ({self.codigo_interno_gerado})"

    def save(self, *args, **kwargs):
        if not self.pk:  # Apenas na criação de um novo item
            # 1. Encontrar o maior codigo_interno_item para esta categoria
            ultimo_item = ItemEstocavel.objects.filter(categoria=self.categoria).order_by('-codigo_interno_item').first()
            novo_codigo = (ultimo_item.codigo_interno_item + 1) if ultimo_item else 1
            self.codigo_interno_item = novo_codigo

            # 2. Gerar o código interno completo
            prefixo = self.categoria.codigo_categoria
            self.codigo_interno_gerado = f"{prefixo}-{self.codigo_interno_item:04d}" # Formata com 4 dígitos, ex: PNL-0001
        
        super().save(*args, **kwargs)

class Lote(models.Model):
    """
    Controla a entrada de um lote específico de um item em estoque.
    """
    item = models.ForeignKey(ItemEstocavel, on_delete=models.PROTECT, related_name='lotes')
    quantidade_inicial = models.DecimalField(max_digits=12, decimal_places=4, help_text="Quantidade que entrou neste lote.")
    quantidade_atual = models.DecimalField(max_digits=12, decimal_places=4, help_text="Quantidade que ainda resta neste lote.")
    custo_unitario_compra = models.DecimalField(max_digits=10, decimal_places=4, help_text="Custo de compra por unidade deste lote.")
    data_entrada = models.DateField(auto_now_add=True, help_text="Data em que o lote entrou em armazém.")
    # Futuramente, podemos adicionar um ForeignKey para um modelo de Fornecedor

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ['data_entrada'] # Garante que o lote mais antigo (FIFO) seja usado primeiro

    def __str__(self):
        return f"Lote de {self.item.nome} - Restam {self.quantidade_atual} de {self.quantidade_inicial}"

    def save(self, *args, **kwargs):
        if not self.pk:  # Apenas na criação de um novo lote
            self.quantidade_atual = self.quantidade_inicial
        super().save(*args, **kwargs)

class MovimentoEstoque(models.Model):
    """
    Registra todas as transações de entrada e saída, garantindo rastreabilidade total.
    """
    TIPO_MOVIMENTO_CHOICES = [
        ('ENTRADA', 'Entrada (Compra)'),
        ('SAIDA', 'Saída (Consumo de Produção)'),
        ('AJUSTE_P', 'Ajuste Positivo'),
        ('AJUSTE_N', 'Ajuste Negativo'),
    ]

    lote = models.ForeignKey(Lote, on_delete=models.PROTECT, related_name='movimentos')
    quantidade = models.DecimalField(max_digits=12, decimal_places=4, help_text="Quantidade movimentada. Positiva para entradas, negativa para saídas.")
    tipo = models.CharField(max_length=10, choices=TIPO_MOVIMENTO_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(User, on_delete=models.PROTECT)

    # Ligação à origem do movimento (opcional, mas muito útil)
    # Aponta para o ItemConsumido que gerou a saída de estoque
    origem_consumo = models.ForeignKey('consumos.ItemConsumido', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimentos_estoque')
    observacao = models.TextField(blank=True, null=True, help_text="Observações ou justificativa para o movimento.")

    class Meta:
        verbose_name = "Movimento de Estoque"
        verbose_name_plural = "Movimentos de Estoque"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade} no {self.lote}"