from django import forms
from django.forms import inlineformset_factory
from .models import (
    Categoria, Atributo,
    ProdutoTemplate, TemplateAtributo, TemplateComponente, FormulaTemplate,
    ProdutoConfiguracao, ConfiguracaoComponenteEscolha, ProdutoInstancia, InstanciaAtributo, InstanciaComponente, Componente
)

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

class AtributoForm(forms.ModelForm):
    class Meta:
        model = Atributo
        fields = '__all__'

class ProdutoTemplateForm(forms.ModelForm):
    class Meta:
        model = ProdutoTemplate
        fields = '__all__'

class TemplateAtributoForm(forms.ModelForm):
    class Meta:
        model = TemplateAtributo
        fields = '__all__'

class TemplateComponenteForm(forms.ModelForm):
    class Meta:
        model = TemplateComponente
        fields = '__all__'

class FormulaTemplateForm(forms.ModelForm):
    class Meta:
        model = FormulaTemplate
        fields = '__all__'

class ProdutoConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = ProdutoConfiguracao
        fields = '__all__'

class ConfiguracaoComponenteEscolhaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoComponenteEscolha
        fields = '__all__'

class ProdutoInstanciaForm(forms.ModelForm):
    class Meta:
        model = ProdutoInstancia
        fields = '__all__'

class InstanciaAtributoForm(forms.ModelForm):
    class Meta:
        model = InstanciaAtributo
        fields = '__all__'

class InstanciaComponenteForm(forms.ModelForm):
    class Meta:
        model = InstanciaComponente
        fields = '__all__'

TemplateAtributoFormSet = inlineformset_factory(
    ProdutoTemplate, 
    TemplateAtributo, 
    fields=('atributo', 'obrigatorio', 'ordem'), 
    extra=1, 
    can_delete=True
)

ConfiguracaoComponenteEscolhaFormSet = inlineformset_factory(
    ProdutoConfiguracao,
    ConfiguracaoComponenteEscolha,
    fields=('template_componente', 'componente_real'),
    extra=1,
    can_delete=True
)

InstanciaAtributoFormSet = inlineformset_factory(
    ProdutoInstancia, 
    InstanciaAtributo, 
    fields=('template_atributo', 'valor_texto', 'valor_num'), 
    extra=1, 
    can_delete=True
)

InstanciaComponenteFormSet = inlineformset_factory(
    ProdutoInstancia, 
    InstanciaComponente, 
    fields=('componente', 'quantidade', 'custo_unitario', 'descricao_detalhada'), 
    extra=1, 
    can_delete=True
)