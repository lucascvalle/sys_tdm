from django import forms
from .models import (
    Categoria, Atributo, ItemMaterial,
    ProdutoTemplate, TemplateAtributo, TemplateComponente, FormulaTemplate,
    ProdutoInstancia, InstanciaAtributo, InstanciaComponente
)

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

class AtributoForm(forms.ModelForm):
    class Meta:
        model = Atributo
        fields = '__all__'

class ItemMaterialForm(forms.ModelForm):
    class Meta:
        model = ItemMaterial
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