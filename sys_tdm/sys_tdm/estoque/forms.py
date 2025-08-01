from django import forms
from .models import ItemEstocavel

class AjusteEstoqueForm(forms.Form):
    item_estocavel = forms.ModelChoiceField(
        queryset=ItemEstocavel.objects.order_by('nome'),
        label="Item a Ajustar"
    )
    nova_quantidade_fisica = forms.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        label="Nova Quantidade Física Correta"
    )
    justificativa = forms.CharField(
        widget=forms.Textarea,
        label="Justificativa",
        help_text="Motivo do ajuste (ex: contagem de inventário, perda, dano)."
    )
