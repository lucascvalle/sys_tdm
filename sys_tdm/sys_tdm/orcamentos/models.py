"""
Models for the Orcamentos (Budgets) application.

This module defines the data structure for budgets (Orcamento) and their
line items (ItemOrcamento), forming the core of the budgeting system.
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
    from produtos.models import ProdutoInstancia, ProdutoConfiguracao


class Orcamento(models.Model):
    """
    Represents a budget, which is a collection of items for a client.

    Each budget has a unique legacy code, a version, and is associated with a user.
    It also stores client-specific information extracted from the legacy code.
    """
    codigo_legado = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Código Legado"),
        help_text=_("O código único original para o orçamento.")
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_("Usuário"),
        help_text=_("O usuário que criou ou é responsável por este orçamento.")
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Criado em"),
        help_text=_("Data e hora de criação do orçamento.")
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Atualizado em"),
        help_text=_("Última data e hora de atualização do orçamento.")
    )
    versao = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Versão"),
        help_text=_("Número da versão do orçamento.")
    )
    versao_base = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Versão Base"),
        help_text=_("Indica a versão do orçamento que serviu de base (para versões >1).")
    )
    # Novos campos para armazenar dados extraídos do codigo_legado
    nome_cliente = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_("Nome do Cliente"),
        help_text=_("Nome completo do cliente associado a este orçamento.")
    )
    tipo_cliente = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_("Tipo de Cliente"),
        help_text=_("Tipo de cliente (ex: 'EP' para Empresa, 'PC' para Particular).")
    )
    codigo_cliente = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Código do Cliente"),
        help_text=_("Código de identificação do cliente.")
    )
    data_solicitacao = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("Data de Solicitação"),
        help_text=_("Data em que o orçamento foi solicitado.")
    )
    codigo_agente = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Código do Agente"),
        help_text=_("Código do agente responsável pelo orçamento (ex: '80-ELLA').")
    )

    class Meta:
        verbose_name = _("Orçamento")
        verbose_name_plural = _("Orçamentos")
        ordering = ['criado_em']
        constraints = [
            models.UniqueConstraint(
                fields=['codigo_legado', 'versao'],
                name='unique_codigo_versao'
            )
        ]

    def __str__(self) -> str:
        """Returns the string representation of the Orcamento."""
        return f"Orçamento {self.codigo_legado} v{self.versao}"


class ItemOrcamento(models.Model):
    """
    Represents a single line item within a budget.

    An item can be a manual entry, a product configuration, or a specific
    product instance. It tracks quantity, unit price, margin, and total.
    """
    orcamento = models.ForeignKey(
        Orcamento,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name=_("Orçamento"),
        help_text=_("O orçamento ao qual este item pertence.")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("Item Pai"),
        help_text=_("Item de orçamento pai, se este for um sub-item.")
    )
    codigo_item_manual = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Código Manual do Item"),
        help_text=_("Código manual do item no orçamento (ex: P01), se não for um produto configurado.")
    )
    # Relacionamento com a configuração do produto, que é mais geral
    configuracao = models.ForeignKey(
        "produtos.ProdutoConfiguracao",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Configuração de Produto"),
        help_text=_("A configuração de produto associada a este item, se aplicável.")
    )
    # Relacionamento com a instância específica do produto (pode ser nulo para itens de template)
    instancia = models.ForeignKey(
        "produtos.ProdutoInstancia",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Instância de Produto"),
        help_text=_("A instância de produto específica associada a este item, se aplicável.")
    )
    # Campos para informações de preço e quantidade
    preco_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name=_("Preço Unitário"),
        help_text=_("Preço unitário do item.")
    )
    quantidade = models.PositiveIntegerField(
        verbose_name=_("Quantidade"),
        help_text=_("Quantidade do item no orçamento.")
    )
    margem_negocio = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        default=0.0,
        verbose_name=_("Margem de Negócio (%)"),
        help_text=_("Margem de negócio aplicada ao preço do item (em percentagem).")
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("Total"),
        help_text=_("Valor total do item (Preço Unitário * Quantidade).")
    )

    class Meta:
        verbose_name = _("Item do Orçamento")
        verbose_name_plural = _("Itens do Orçamento")
        ordering = ['id']

    def save(self, *args, **kwargs):
        """
        Overrides the save method to automatically calculate the total price
        before saving the object.
        """
        # O cálculo do total pode precisar de lógica mais complexa
        # dependendo se é um item pai ou filho.
        self.total = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Returns the string representation of the ItemOrcamento."""
        if self.instancia:
            return f"Item: {self.instancia.codigo} - {self.instancia.configuracao.nome}"
        elif self.configuracao:
            return f"Configuração: {self.configuracao.nome}"
        else:
            return f"Item de Orçamento {self.id}"
