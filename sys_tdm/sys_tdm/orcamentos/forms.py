from django import forms
from .models import Orcamento, ItemOrcamento

class OrcamentoForm(forms.ModelForm):
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

class ItemOrcamentoForm(forms.ModelForm):
    class Meta:
        model = ItemOrcamento
        fields = [
            'instancia',
            'preco_unitario',
            'quantidade',
            # 'total' é calculado no método save do modelo
        ]