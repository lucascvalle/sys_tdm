"""
Models for the Estoque (Stock) application.

This module defines the data structures for managing inventory items,
including categories, stockable items, batches (lotes), and stock movements.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

# Get the User model for ForeignKey relationships
User = get_user_model()

# Type checking for potential circular imports
if TYPE_CHECKING:
    from consumos.models import ItemConsumido


class CategoriaItem(models.Model):
    """
    Hierarchical categories for stock items.

    Example: Raw Material > Panels > MDF. Categories help organize and filter
    stockable items.
    """
    nome = models.CharField(
        max_length=100,
        help_text=_("Ex: Ferragens, Painéis de Madeira, Consumíveis"),
        verbose_name=_("Nome da Categoria")
    )
    codigo_categoria = models.CharField(
        max_length=10,
        unique=True,
        help_text=_("Prefixo único para esta categoria (ex: FER, PNL, QMC)."),
        null=True,
        verbose_name=_("Código da Categoria")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategorias',
        verbose_name=_("Categoria Pai"),
        help_text=_("A categoria superior a esta, se for uma subcategoria.")
    )

    class Meta:
        verbose_name = _("Categoria de Item")
        verbose_name_plural = _("Categorias de Itens")
        unique_together = ('nome', 'parent')
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the category."""
        if self.parent:
            return f"{self.parent} > {self.nome}"
        return self.nome


class ItemEstocavel(models.Model):
    """
    Represents a physical, purchasable item that exists in stock.
    This is the "Simple Product" in the inventory.
    """
    UNIDADE_CHOICES = [
        ('un', _('Unidade')),
        ('m', _('Metro Linear')),
        ('m2', _('Metro Quadrado')),
        ('m3', _('Metro Cúbico')),
        ('kg', _('Quilograma')),
        ('L', _('Litro')),
    ]

    categoria = models.ForeignKey(
        CategoriaItem,
        on_delete=models.PROTECT,
        related_name='itens',
        verbose_name=_("Categoria"),
        help_text=_("A categoria à qual este item estocável pertence.")
    )
    nome = models.CharField(
        max_length=255,
        help_text=_("Ex: Painel MDF Hidrófugo 19mm 2440x1220"),
        verbose_name=_("Nome do Item")
    )
    descricao = models.TextField(
        blank=True,
        help_text=_("Detalhes técnicos, fornecedor, etc."),
        verbose_name=_("Descrição")
    )
    
    codigo_sku_fornecedor = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("SKU (Stock Keeping Unit) ou código de barras do fornecedor."),
        verbose_name=_("Código SKU Fornecedor")
    )

    codigo_interno_item = models.PositiveIntegerField(
        editable=False,
        help_text=_("Código sequencial do item dentro da categoria."),
        null=True,
        verbose_name=_("Código Interno Sequencial")
    )
    codigo_interno_gerado = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text=_("Código interno completo gerado automaticamente (ex: PNL-0001)."),
        null=True,
        verbose_name=_("Código Interno Gerado")
    )

    unidade_medida = models.CharField(
        max_length=5,
        choices=UNIDADE_CHOICES,
        default='un',
        verbose_name=_("Unidade de Medida"),
        help_text=_("Unidade de medida para este item (ex: Unidade, Metro, Kg).")
    )

    largura_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Largura em milímetros"),
        verbose_name=_("Largura (mm)")
    )
    altura_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Altura ou comprimento em milímetros"),
        verbose_name=_("Altura/Comprimento (mm)")
    )
    espessura_mm = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Espessura em milímetros"),
        verbose_name=_("Espessura (mm)")
    )

    class Meta:
        verbose_name = _("Item Estocável")
        verbose_name_plural = _("Itens Estocáveis")
        unique_together = ('categoria', 'codigo_interno_item')
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the stockable item."""
        return f"{self.nome} ({self.codigo_interno_gerado})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Overrides the save method to automatically generate `codigo_interno_item`
        and `codigo_interno_gerado` upon creation.
        """
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
    Controls the entry of a specific batch of an item into stock.

    Each batch has an initial quantity, a current quantity, a unit purchase cost,
    and an entry date. It's crucial for FIFO (First In, First Out) inventory management.
    """
    item = models.ForeignKey(
        ItemEstocavel,
        on_delete=models.PROTECT,
        related_name='lotes',
        verbose_name=_("Item Estocável"),
        help_text=_("O item estocável ao qual este lote pertence.")
    )
    quantidade_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text=_("Quantidade que entrou neste lote."),
        verbose_name=_("Quantidade Inicial")
    )
    quantidade_atual = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text=_("Quantidade que ainda resta neste lote."),
        verbose_name=_("Quantidade Atual")
    )
    custo_unitario_compra = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        help_text=_("Custo de compra por unidade deste lote."),
        verbose_name=_("Custo Unitário de Compra")
    )
    data_entrada = models.DateField(
        auto_now_add=True,
        help_text=_("Data em que o lote entrou em armazém."),
        verbose_name=_("Data de Entrada")
    )
    # Futuramente, podemos adicionar um ForeignKey para um modelo de Fornecedor

    class Meta:
        verbose_name = _("Lote")
        verbose_name_plural = _("Lotes")
        ordering = ['data_entrada'] # Garante que o lote mais antigo (FIFO) seja usado primeiro

    def __str__(self) -> str:
        """Returns the string representation of the batch."""
        return f'{_("Lote de")} {self.item.nome} - {_("Restam")} {self.quantidade_atual} de {self.quantidade_inicial}'

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Overrides the save method to set `quantidade_atual` to `quantidade_inicial`
        upon creation of a new batch.
        """
        if not self.pk:  # Apenas na criação de um novo lote
            self.quantidade_atual = self.quantidade_inicial
        super().save(*args, **kwargs)

    def get_latest_cost(self) -> float:
        """
        Returns the unit cost of this batch. This method is a placeholder
        and might be expanded to consider average cost or other methodologies.
        """
        return float(self.custo_unitario_compra)


class MovimentoEstoque(models.Model):
    """
    Records all stock transactions (in and out), ensuring full traceability.
    """
    TIPO_MOVIMENTO_CHOICES = [
        ('ENTRADA', _('Entrada (Compra)')),
        ('SAIDA', _('Saída (Consumo de Produção)')),
        ('AJUSTE_P', _('Ajuste Positivo')),
        ('AJUSTE_N', _('Ajuste Negativo')),
    ]

    lote = models.ForeignKey(
        Lote,
        on_delete=models.PROTECT,
        related_name='movimentos',
        verbose_name=_("Lote"),
        help_text=_("O lote ao qual este movimento de estoque se refere.")
    )
    quantidade = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text=_("Quantidade movimentada. Positiva para entradas, negativa para saídas."),
        verbose_name=_("Quantidade")
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_MOVIMENTO_CHOICES,
        verbose_name=_("Tipo de Movimento"),
        help_text=_("O tipo de transação de estoque (entrada, saída, ajuste).")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Data/Hora"),
        help_text=_("Data e hora em que o movimento ocorreu.")
    )
    responsavel = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Responsável"),
        help_text=_("O usuário responsável por este movimento de estoque.")
    )

    # Ligação à origem do movimento (opcional, mas muito útil)
    # Aponta para o ItemConsumido que gerou a saída de estoque
    origem_consumo = models.ForeignKey(
        'consumos.ItemConsumido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentos_estoque',
        verbose_name=_("Origem do Consumo"),
        help_text=_("O item consumido que gerou este movimento de saída de estoque, se aplicável.")
    )
    observacao = models.TextField(
        blank=True,
        null=True,
        help_text=_("Observações ou justificativa para o movimento."),
        verbose_name=_("Observação")
    )

    class Meta:
        verbose_name = _("Movimento de Estoque")
        verbose_name_plural = _("Movimentos de Estoque")
        ordering = ['timestamp']

    def __str__(self) -> str:
        """Returns the string representation of the stock movement."""
        return f"{self.get_tipo_display()} " + _("de") + f" {self.quantidade} " + _("no") + f" {self.lote}"
