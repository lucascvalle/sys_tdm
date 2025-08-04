"""
Forms for the Orcamentos (Budgets) application.

This module defines Django forms for creating and editing budgets and their items.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Orcamento, ItemOrcamento


class OrcamentoForm(forms.ModelForm):
    """
    A form for editing the main details of an `Orcamento`.
    """
    class Meta:
        model = Orcamento
        fields = [
            'codigo_legado',
            'nome_cliente',
            'tipo_cliente',
            'codigo_cliente',
            'data_solicitacao',
            'codigo_agente',
            # 'usuario', 'criado_em', 'atualizado_em', 'versao', 'versao_base' são gerenciados pelo sistema
        ]
        widgets = {
            'data_solicitacao': forms.DateInput(attrs={'type': 'date'}),
        }


class CriarOrcamentoForm(forms.ModelForm):
    """
    A form for creating a new `Orcamento`.

    It focuses on the `codigo_legado` field, which is used to automatically
    populate other budget details.
    """
    class Meta:
        model = Orcamento
        fields = ['codigo_legado']


class ItemOrcamentoForm(forms.ModelForm):
    """
    A form for adding and editing an `ItemOrcamento`.
    """
    class Meta:
        model = ItemOrcamento
        fields = [
            'instancia',
            'preco_unitario',
            'quantidade',
            'margem_negocio',
            # 'total' é calculado no método save do modelo
        ]