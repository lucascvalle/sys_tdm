"""
Forms for the Consumos (Consumption) application.

This module defines Django forms for managing work order sheets, consumed items,
work sessions, workstations, and operators. It also includes filter forms for reports.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import FichaConsumoObra, ItemConsumido, SessaoTrabalho, PostoTrabalho, Operador
from estoque.models import ItemEstocavel


class OperadorForm(forms.ModelForm):
    """
    Form for creating and updating `Operador` objects.
    """
    class Meta:
        model = Operador
        fields = ['nome']


class PostoTrabalhoForm(forms.ModelForm):
    """
    Form for creating and updating `PostoTrabalho` objects.
    """
    class Meta:
        model = PostoTrabalho
        fields = '__all__'


class FichaConsumoObraForm(forms.ModelForm):
    """
    Form for creating and updating `FichaConsumoObra` objects.
    """
    class Meta:
        model = FichaConsumoObra
        fields = ['ref_obra', 'data_inicio', 'previsao_entrega', 'responsavel', 'status']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'previsao_entrega': forms.DateInput(attrs={'type': 'date'}),
        }


class ItemConsumidoForm(forms.ModelForm):
    """
    Form for creating and updating `ItemConsumido` objects.
    """
    class Meta:
        model = ItemConsumido
        fields = ['data_consumo', 'item_estocavel', 'descricao_detalhada', 'quantidade', 'unidade']
        widgets = {
            'data_consumo': forms.DateInput(attrs={'type': 'date'}),
        }


class SessaoTrabalhoForm(forms.ModelForm):
    """
    Form for creating and updating `SessaoTrabalho` objects.
    """
    class Meta:
        model = SessaoTrabalho
        fields = ['posto_trabalho', 'operador', 'ficha_obra', 'operacao', 'hora_inicio', 'hora_saida']
        widgets = {
            'hora_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'hora_saida': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class MaterialConsumptionReportFilterForm(forms.Form):
    """
    Form for filtering the material consumption report.
    """
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_("Data Início")
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_("Data Fim")
    )
    item_estocavel = forms.ModelChoiceField(
        queryset=ItemEstocavel.objects.all(),
        required=False,
        empty_label=_("Todos os Itens"),
        widget=forms.Select(attrs={'class': 'select2-item-estocavel'}),
        label=_("Item Estocável")
    )
    ficha_obra = forms.ModelChoiceField(
        queryset=FichaConsumoObra.objects.all(),
        required=False,
        empty_label=_("Todas as Obras"),
        widget=forms.Select(attrs={'class': 'select2-ficha-obra'}),
        label=_("Ficha de Obra")
    )


class MachineUtilizationReportFilterForm(forms.Form):
    """
    Form for filtering the machine utilization report.
    """
    posto_trabalho = forms.ModelChoiceField(
        queryset=PostoTrabalho.objects.all(),
        required=False,
        empty_label=_("Todos os Postos"),
        label=_("Posto de Trabalho")
    )
    operador = forms.ModelChoiceField(
        queryset=Operador.objects.all(),
        required=False,
        empty_label=_("Todos os Operadores"),
        label=_("Operador")
    )
    ficha_obra = forms.ModelChoiceField(
        queryset=FichaConsumoObra.objects.all(),
        required=False,
        empty_label=_("Todas as Obras"),
        label=_("Ficha de Obra")
    )
    data = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label=_("Data")
    )