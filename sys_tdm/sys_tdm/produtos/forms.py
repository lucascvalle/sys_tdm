"""
Forms for the Products application.

This module defines Django forms for creating and editing various product-related
entities, including categories, attributes, product templates, configurations,
and instances. It also provides inline formsets for managing related objects.
"""

from django import forms
from django.forms import inlineformset_factory
from django.utils.translation import gettext_lazy as _

from .models import (
    Categoria, Atributo, Componente,
    ProdutoTemplate, TemplateAtributo, TemplateComponente, FormulaTemplate,
    ProdutoConfiguracao, ConfiguracaoComponenteEscolha,
    ProdutoInstancia, InstanciaAtributo, InstanciaComponente
)


class CategoriaForm(forms.ModelForm):
    """
    Form for creating and updating `Categoria` objects.
    """
    class Meta:
        model = Categoria
        fields = '__all__'


class AtributoForm(forms.ModelForm):
    """
    Form for creating and updating `Atributo` objects.
    """
    class Meta:
        model = Atributo
        fields = '__all__'


class ProdutoTemplateForm(forms.ModelForm):
    """
    Form for creating and updating `ProdutoTemplate` objects.
    """
    class Meta:
        model = ProdutoTemplate
        fields = '__all__'


class TemplateAtributoForm(forms.ModelForm):
    """
    Form for creating and updating `TemplateAtributo` objects.
    """
    class Meta:
        model = TemplateAtributo
        fields = '__all__'


class TemplateComponenteForm(forms.ModelForm):
    """
    Form for creating and updating `TemplateComponente` objects.
    """
    class Meta:
        model = TemplateComponente
        fields = '__all__'


class FormulaTemplateForm(forms.ModelForm):
    """
    Form for creating and updating `FormulaTemplate` objects.
    """
    class Meta:
        model = FormulaTemplate
        fields = '__all__'


class ProdutoConfiguracaoForm(forms.ModelForm):
    """
    Form for creating and updating `ProdutoConfiguracao` objects.
    """
    class Meta:
        model = ProdutoConfiguracao
        fields = '__all__'


class ConfiguracaoComponenteEscolhaForm(forms.ModelForm):
    """
    Form for creating and updating `ConfiguracaoComponenteEscolha` objects.
    """
    class Meta:
        model = ConfiguracaoComponenteEscolha
        fields = '__all__'


class ProdutoInstanciaForm(forms.ModelForm):
    """
    Form for creating and updating `ProdutoInstancia` objects.
    """
    class Meta:
        model = ProdutoInstancia
        fields = '__all__'


class InstanciaAtributoForm(forms.ModelForm):
    """
    Form for creating and updating `InstanciaAtributo` objects.
    """
    class Meta:
        model = InstanciaAtributo
        fields = '__all__'


class InstanciaComponenteForm(forms.ModelForm):
    """
    Form for creating and updating `InstanciaComponente` objects.
    """
    class Meta:
        model = InstanciaComponente
        fields = '__all__'


# =============================================================================
# Inline Formsets
# =============================================================================

TemplateAtributoFormSet = inlineformset_factory(
    ProdutoTemplate,
    TemplateAtributo,
    fields=('atributo', 'obrigatorio', 'ordem'),
    extra=1,
    can_delete=True
)
"""
Inline formset for `TemplateAtributo` objects related to a `ProdutoTemplate`.

Allows managing multiple `TemplateAtributo` instances directly within the
`ProdutoTemplate` form.
"""

ConfiguracaoComponenteEscolhaFormSet = inlineformset_factory(
    ProdutoConfiguracao,
    ConfiguracaoComponenteEscolha,
    fields=('template_componente', 'componente_real', 'descricao_personalizada'),
    extra=1,
    can_delete=True
)
"""
Inline formset for `ConfiguracaoComponenteEscolha` objects related to a `ProdutoConfiguracao`.

Allows managing multiple `ConfiguracaoComponenteEscolha` instances directly within the
`ProdutoConfiguracao` form.
"""

InstanciaAtributoFormSet = inlineformset_factory(
    ProdutoInstancia,
    InstanciaAtributo,
    fields=('template_atributo', 'valor_texto', 'valor_num'),
    extra=1,
    can_delete=True
)
"""
Inline formset for `InstanciaAtributo` objects related to a `ProdutoInstancia`.

Allows managing multiple `InstanciaAtributo` instances directly within the
`ProdutoInstancia` form.
"""

InstanciaComponenteFormSet = inlineformset_factory(
    ProdutoInstancia,
    InstanciaComponente,
    fields=('componente', 'quantidade', 'custo_unitario', 'descricao_detalhada'),
    extra=1,
    can_delete=True
)
"""
Inline formset for `InstanciaComponente` objects related to a `ProdutoInstancia`.

Allows managing multiple `InstanciaComponente` instances directly within the
`ProdutoInstancia` form.
"""



