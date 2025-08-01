from django.contrib import admin
from .models import (
    Categoria, Atributo, Componente, ProdutoTemplate, TemplateAtributo, 
    TemplateComponente, ProdutoConfiguracao, ConfiguracaoComponenteEscolha, 
    ProdutoInstancia, InstanciaAtributo, InstanciaComponente, FormulaTemplate
)

# Inlines para facilitar a edição

class TemplateAtributoInline(admin.TabularInline):
    model = TemplateAtributo
    extra = 1
    ordering = ('ordem',)

class TemplateComponenteInline(admin.TabularInline):
    model = TemplateComponente
    extra = 1
    fields = ('componente', 'quantidade_fixa', 'atributo_relacionado', 'formula_calculo', 'fator_perda')

class FormulaTemplateInline(admin.StackedInline):
    model = FormulaTemplate
    extra = 1

class ConfiguracaoComponenteEscolhaInline(admin.TabularInline):
    model = ConfiguracaoComponenteEscolha
    extra = 1
    fields = ('template_componente', 'componente_real', 'descricao_personalizada')

class InstanciaAtributoInline(admin.TabularInline):
    model = InstanciaAtributo
    extra = 1
    fields = ('template_atributo', 'valor_texto', 'valor_num')

class InstanciaComponenteInline(admin.TabularInline):
    model = InstanciaComponente
    extra = 1
    fields = ('componente', 'quantidade', 'custo_unitario', 'descricao_detalhada')
    readonly_fields = ('componente', 'custo_unitario')

# ModelAdmins

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)

@admin.register(Atributo)
class AtributoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo')
    list_filter = ('tipo',)
    search_fields = ('nome',)

@admin.register(Componente)
class ComponenteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'custo_unitario', 'unidade')
    search_fields = ('nome',)
    filter_horizontal = ('itens_compativeis',)

@admin.register(ProdutoTemplate)
class ProdutoTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('nome', 'descricao')
    inlines = [TemplateAtributoInline, TemplateComponenteInline, FormulaTemplateInline]

@admin.register(ProdutoConfiguracao)
class ProdutoConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'template')
    list_filter = ('template__categoria',)
    search_fields = ('nome', 'template__nome')
    inlines = [ConfiguracaoComponenteEscolhaInline]

@admin.register(ProdutoInstancia)
class ProdutoInstanciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'configuracao', 'quantidade')
    list_filter = ('configuracao__template__categoria',)
    search_fields = ('codigo', 'configuracao__nome')
    inlines = [InstanciaAtributoInline, InstanciaComponenteInline]
    readonly_fields = ('configuracao',)