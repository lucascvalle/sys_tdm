from django import forms
from .models import FichaConsumoObra, ItemConsumido, SessaoTrabalho, PostoTrabalho, Operador
from estoque.models import ItemEstocavel # Importa o novo modelo

class OperadorForm(forms.ModelForm):
    class Meta:
        model = Operador
        fields = ['nome']

class PostoTrabalhoForm(forms.ModelForm):
    class Meta:
        model = PostoTrabalho
        fields = '__all__'

class FichaConsumoObraForm(forms.ModelForm):
    class Meta:
        model = FichaConsumoObra
        fields = ['ref_obra', 'data_inicio', 'previsao_entrega', 'responsavel', 'status']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'previsao_entrega': forms.DateInput(attrs={'type': 'date'}),
        }

class ItemConsumidoForm(forms.ModelForm):
    class Meta:
        model = ItemConsumido
        fields = ['data_consumo', 'item_estocavel', 'descricao_detalhada', 'quantidade', 'unidade']
        widgets = {
            'data_consumo': forms.DateInput(attrs={'type': 'date'}),
        }

class SessaoTrabalhoForm(forms.ModelForm):
    class Meta:
        model = SessaoTrabalho
        fields = ['posto_trabalho', 'operador', 'ficha_obra', 'operacao', 'hora_inicio', 'hora_saida']
        widgets = {
            'hora_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'hora_saida': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class MaterialConsumptionReportFilterForm(forms.Form):
    data_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    data_fim = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    item_estocavel = forms.ModelChoiceField(queryset=ItemEstocavel.objects.all(), required=False, empty_label="Todos os Itens")
    ficha_obra = forms.ModelChoiceField(queryset=FichaConsumoObra.objects.all(), required=False, empty_label="Todas as Obras")

class MachineUtilizationReportFilterForm(forms.Form):
    posto_trabalho = forms.ModelChoiceField(queryset=PostoTrabalho.objects.all(), required=False, empty_label="Todos os Postos")
    operador = forms.ModelChoiceField(queryset=Operador.objects.all(), required=False, empty_label="Todos os Operadores")
    ficha_obra = forms.ModelChoiceField(queryset=FichaConsumoObra.objects.all(), required=False, empty_label="Todas as Obras")
    data = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
