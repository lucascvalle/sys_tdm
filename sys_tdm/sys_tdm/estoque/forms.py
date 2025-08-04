"""
Forms for the Estoque (Stock) application.

This module defines Django forms for managing stock adjustments and batch entries.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ItemEstocavel, Lote


class AjusteEstoqueForm(forms.Form):
    """
    Form for performing stock adjustments on `ItemEstocavel`.

    Allows specifying a new physical quantity and a justification for the adjustment.
    """
    item_estocavel = forms.ModelChoiceField(
        queryset=ItemEstocavel.objects.all(),
        label=_("Item a ser Ajustado"),
        empty_label=_("Selecione um item..."),
        widget=forms.Select(attrs={'class': 'form-control select2-field'}),
        help_text=_("Selecione o item de estoque para o qual deseja realizar o ajuste.")
    )
    nova_quantidade_fisica = forms.DecimalField(
        label=_("Nova Quantidade Física Correta"),
        max_digits=12,
        decimal_places=4,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_("Informe a quantidade total física correta do item em estoque. O sistema calculará a diferença e registrará o ajuste (positivo ou negativo).")
    )
    justificativa = forms.CharField(
        label=_("Justificativa"),
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False,
        help_text=_("Descreva o motivo do ajuste de estoque.")
    )


class LoteForm(forms.ModelForm):
    """
    Form for registering new `Lote` entries (stock receipts).
    """
    class Meta:
        model = Lote
        fields = ['item', 'quantidade_inicial', 'custo_unitario_compra']
        labels = {
            'item': _("Item Estocável"),
            'quantidade_inicial': _("Quantidade Inicial"),
            'custo_unitario_compra': _("Custo Unitário de Compra"),
        }
        help_texts = {
            'item': _("Selecione o item estocável que está sendo recebido."),
            'quantidade_inicial': _("A quantidade total do item neste lote."),
            'custo_unitario_compra': _("O custo por unidade do item neste lote."),
        }