"""
Models for the Consumos (Consumption) application.

This module defines the data structures for tracking material consumption
and work sessions related to specific production orders (fichas de obra).
"""

from __future__ import annotations
from typing import Any, TYPE_CHECKING

from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

# Type checking for potential circular imports
if TYPE_CHECKING:
    from estoque.models import ItemEstocavel, Lote, MovimentoEstoque


class PostoTrabalho(models.Model):
    """
    Represents a workstation or machine in the factory.

    Used to track where work sessions take place and their associated costs.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Ex: Serra de Bancada, CNC 1, Bancada de Montagem"),
        verbose_name=_("Nome do Posto de Trabalho")
    )
    custo_hora = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Custo operacional por hora do posto"),
        verbose_name=_("Custo por Hora")
    )

    class Meta:
        verbose_name = _("Posto de Trabalho")
        verbose_name_plural = _("Postos de Trabalho")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the workstation."""
        return self.nome


class FichaConsumoObra(models.Model):
    """
    Represents a complete work order sheet, filled over several days.

    It tracks the overall progress and status of a production order.
    """
    STATUS_CHOICES = [
        ('planejada', _('Planejada')),
        ('em_andamento', _('Em Andamento')),
        ('concluida', _('Concluída')),
        ('cancelada', _('Cancelada')),
    ]

    ref_obra = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("O código ou nome único da obra"),
        verbose_name=_("Referência da Obra")
    )
    data_inicio = models.DateField(
        help_text=_("A data de início dos trabalhos na obra"),
        verbose_name=_("Data de Início")
    )
    previsao_entrega = models.DateField(
        help_text=_("A data prevista para a conclusão"),
        verbose_name=_("Previsão de Entrega")
    )
    responsavel = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='fichas_consumo',
        verbose_name=_("Responsável"),
        help_text=_("O usuário responsável por esta ficha de consumo.")
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planejada',
        verbose_name=_("Status"),
        help_text=_("O status atual da ficha de consumo da obra.")
    )

    class Meta:
        verbose_name = _("Ficha de Consumo de Obra")
        verbose_name_plural = _("Fichas de Consumo de Obra")
        ordering = ['ref_obra']

    def __str__(self) -> str:
        """Returns the string representation of the work order sheet."""
        return str(_("Ficha")) + " " + self.ref_obra + " (" + self.get_status_display() + ")"


class ItemConsumido(models.Model):
    """
    Represents a single record of material consumption (raw material or component)
    within a `FichaConsumoObra`.

    This model triggers stock movements upon saving.
    """
    ficha_obra = models.ForeignKey(
        FichaConsumoObra,
        on_delete=models.CASCADE,
        related_name='itens_consumidos',
        verbose_name=_("Ficha de Obra"),
        help_text=_("A ficha de consumo de obra à qual este item consumido pertence.")
    )
    data_consumo = models.DateField(
        help_text=_("O dia em que o material foi efetivamente consumido"),
        verbose_name=_("Data de Consumo")
    )

    # O ForeignKey agora aponta para o item físico em estoque
    item_estocavel = models.ForeignKey(
        'estoque.ItemEstocavel',
        on_delete=models.PROTECT,
        related_name='consumos',
        null=True,
        verbose_name=_("Item Estocável"),
        help_text=_("O item físico do estoque que foi consumido.")
    )
    
    descricao_detalhada = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text=_("Ex: HTD-H1000, Cor: Branco"),
        verbose_name=_("Descrição Detalhada")
    )

    quantidade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Quantidade"),
        help_text=_("Quantidade do item consumido.")
    )
    unidade = models.CharField(
        max_length=10,
        help_text=_("Ex: m, kg, un"),
        verbose_name=_("Unidade")
    )

    class Meta:
        verbose_name = _("Item Consumido")
        verbose_name_plural = _("Itens Consumidos")
        ordering = ['data_consumo']

    def __str__(self) -> str:
        """Returns the string representation of the consumed item."""
        return f"{self.quantidade} {self.unidade} " + str(_("de")) + f" {self.item_estocavel.nome} " + str(_("em")) + f" {self.data_consumo}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Overrides the save method to handle stock deduction and create `MovimentoEstoque`.

        This method ensures that when an `ItemConsumido` is saved, the corresponding
        quantity is deducted from available stock batches (FIFO) and a stock movement
        record is created.

        Raises:
            ValidationError: If there is insufficient stock for the consumption.
        """
        # Import inside the method to avoid circular imports
        from estoque.models import Lote, MovimentoEstoque

        # Envolve toda a lógica em uma transação para garantir a integridade dos dados
        with transaction.atomic():
            # Verifica se há estoque suficiente
            total_disponivel = Lote.objects.filter(item=self.item_estocavel).aggregate(total=Sum('quantidade_atual'))['total'] or 0
            if total_disponivel < self.quantidade:
                raise ValidationError(
                    _("Estoque insuficiente para {item_name}. Disponível: {available}, Necessário: {needed}").format(
                        item_name=self.item_estocavel.nome,
                        available=total_disponivel,
                        needed=self.quantidade
                    )
                )

            # Salva o ItemConsumido primeiro para ter um ID
            super().save(*args, **kwargs)

            quantidade_a_deduzir = self.quantidade
            lotes_disponiveis = Lote.objects.filter(item=self.item_estocavel, quantidade_atual__gt=0).order_by('data_entrada')

            for lote in lotes_disponiveis:
                if quantidade_a_deduzir <= 0:
                    break

                quantidade_do_lote = min(lote.quantidade_atual, quantidade_a_deduzir)
                
                # Deduz do lote
                lote.quantidade_atual -= quantidade_do_lote
                lote.save()

                # Cria o movimento de estoque
                MovimentoEstoque.objects.create(
                    lote=lote,
                    quantidade=-quantidade_do_lote, # Saída é negativa
                    tipo='SAIDA',
                    responsavel=self.ficha_obra.responsavel, # Assumindo que o responsável da ficha é quem aciona
                    origem_consumo=self
                )

                quantidade_a_deduzir -= quantidade_do_lote


class Operador(models.Model):
    """
    Represents an operator (employee) in the factory.
    """
    nome = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Nome do Operador"),
        help_text=_("Nome completo do operador.")
    )

    class Meta:
        verbose_name = _("Operador")
        verbose_name_plural = _("Operadores")
        ordering = ['nome']

    def __str__(self) -> str:
        """Returns the string representation of the operator."""
        return self.nome


class SessaoTrabalho(models.Model):
    """
    Represents a single work session or machine usage record.

    It tracks the time spent by an operator at a specific workstation for a work order.
    """
    posto_trabalho = models.ForeignKey(
        PostoTrabalho,
        on_delete=models.PROTECT,
        related_name='sessoes_trabalho',
        verbose_name=_("Posto de Trabalho"),
        help_text=_("O posto de trabalho ou máquina utilizada nesta sessão.")
    )
    operador = models.ForeignKey(
        Operador,
        on_delete=models.PROTECT,
        related_name='sessoes_trabalho',
        verbose_name=_("Operador"),
        help_text=_("O operador que realizou o trabalho nesta sessão.")
    )
    ficha_obra = models.ForeignKey(
        FichaConsumoObra,
        on_delete=models.PROTECT,
        related_name='sessoes_trabalho_relacionadas',
        null=True,
        blank=True,
        verbose_name=_("Ficha de Obra"),
        help_text=_("A ficha de consumo de obra à qual esta sessão de trabalho está relacionada.")
    )
    operacao = models.TextField(
        help_text=_("Descrição da tarefa realizada"),
        verbose_name=_("Operação")
    )
    hora_inicio = models.DateTimeField(
        help_text=_("Data e hora de início da tarefa"),
        verbose_name=_("Hora de Início")
    )
    hora_saida = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Data e hora de término da tarefa"),
        verbose_name=_("Hora de Término")
    )

    class Meta:
        verbose_name = _("Sessão de Trabalho")
        verbose_name_plural = _("Sessões de Trabalho")
        ordering = ['-hora_inicio']

    def __str__(self) -> str:
        """Returns the string representation of the work session."""
        obra_ref = self.ficha_obra.ref_obra if self.ficha_obra else _("N/A")
        return str(_("Sessão em")) + f" {self.posto_trabalho} " + str(_("por")) + f" {self.operador} " + str(_("para obra")) + f" {obra_ref}"
