"""
Admin configuration for the Products application.

This module registers the product-related models with the Django admin site
and customizes their appearance and behavior, using inlines for easier
management of related objects.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    Categoria, Atributo, Componente, ProdutoTemplate, TemplateAtributo,
    TemplateComponente, ProdutoConfiguracao, ConfiguracaoComponenteEscolha,
    ProdutoInstancia, InstanciaAtributo, InstanciaComponente, FormulaTemplate
)


# =============================================================================
# Inlines for related models
# =============================================================================

class TemplateAtributoInline(admin.TabularInline):
    """
    Inline for `TemplateAtributo` to manage attributes directly within `ProdutoTemplate` admin.
    """
    model = TemplateAtributo
    extra = 1
    ordering = ('ordem',)
    verbose_name = _("Atributo do Template")
    verbose_name_plural = _("Atributos do Template")


class TemplateComponenteInline(admin.TabularInline):
    """
    Inline for `TemplateComponente` to manage components directly within `ProdutoTemplate` admin.
    """
    model = TemplateComponente
    extra = 1
    fields = ('componente', 'quantidade_fixa', 'atributo_relacionado', 'formula_calculo', 'fator_perda')
    verbose_name = _("Componente do Template")
    verbose_name_plural = _("Componentes do Template")


class FormulaTemplateInline(admin.StackedInline):
    """
    Inline for `FormulaTemplate` to manage global formulas directly within `ProdutoTemplate` admin.
    """
    model = FormulaTemplate
    extra = 1
    verbose_name = _("Fórmula Global do Template")
    verbose_name_plural = _("Fórmulas Globais do Template")


class ConfiguracaoComponenteEscolhaInline(admin.TabularInline):
    """
    Inline for `ConfiguracaoComponenteEscolha` to manage component choices
    directly within `ProdutoConfiguracao` admin.
    """
    model = ConfiguracaoComponenteEscolha
    extra = 1
    fields = ('template_componente', 'componente_real', 'descricao_personalizada')
    verbose_name = _("Escolha de Componente")
    verbose_name_plural = _("Escolhas de Componentes")


class InstanciaAtributoInline(admin.TabularInline):
    """
    Inline for `InstanciaAtributo` to manage attribute values directly within `ProdutoInstancia` admin.
    """
    model = InstanciaAtributo
    extra = 1
    fields = ('template_atributo', 'valor_texto', 'valor_num')
    verbose_name = _("Atributo da Instância")
    verbose_name_plural = _("Atributos da Instância")


class InstanciaComponenteInline(admin.TabularInline):
    """
    Inline for `InstanciaComponente` to display and manage components
    associated with a `ProdutoInstancia`.
    """
    model = InstanciaComponente
    extra = 1
    fields = ('componente', 'quantidade', 'custo_unitario', 'descricao_detalhada')
    readonly_fields = ('componente', 'custo_unitario') # These fields are typically calculated or set automatically
    verbose_name = _("Componente da Instância")
    verbose_name_plural = _("Componentes da Instância")


# =============================================================================
# ModelAdmin registrations
# =============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin options for the `Categoria` model."""
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)


@admin.register(Atributo)
class AtributoAdmin(admin.ModelAdmin):
    """Admin options for the `Atributo` model."""
    list_display = ('nome', 'tipo')
    list_filter = ('tipo',)
    search_fields = ('nome',)


@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    """Admin options for the `Componente` model."""
    list_display = ('nome', 'custo_unitario', 'unidade')
    search_fields = ('nome',)
    filter_horizontal = ('itens_compativeis',)


@admin.register(ProdutoTemplate)
class ProdutoTemplateAdmin(admin.ModelAdmin):
    """Admin options for the `ProdutoTemplate` model."""
    list_display = ('nome', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('nome', 'descricao_instancia_template')
    inlines = [TemplateAtributoInline, TemplateComponenteInline, FormulaTemplateInline]


@admin.register(ProdutoConfiguracao)
class ProdutoConfiguracaoAdmin(admin.ModelAdmin):
    """Admin options for the `ProdutoConfiguracao` model."""
    list_display = ('nome', 'template')
    list_filter = ('template__categoria',)
    search_fields = ('nome', 'template__nome', 'descricao_configuracao_template')
    inlines = [ConfiguracaoComponenteEscolhaInline]


@admin.register(ProdutoInstancia)
class ProdutoInstanciaAdmin(admin.ModelAdmin):
    """Admin options for the `ProdutoInstancia` model."""
    list_display = ('codigo', 'configuracao', 'quantidade')
    list_filter = ('configuracao__template__categoria',)
    search_fields = ('codigo', 'configuracao__nome')
    inlines = [InstanciaAtributoInline, InstanciaComponenteInline]
    readonly_fields = ('configuracao',) # Configuration is set upon creation and should not be changed directly
