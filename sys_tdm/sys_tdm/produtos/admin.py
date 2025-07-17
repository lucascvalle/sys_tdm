from django.contrib import admin
from .models import (
    Categoria, Atributo, ItemMaterial,
    ProdutoTemplate, TemplateAtributo, TemplateComponente, FormulaTemplate,
    ProdutoInstancia, InstanciaAtributo, InstanciaComponente
)

# Inlines para facilitar a edição

class TemplateAtributoInline(admin.TabularInline):
    model = TemplateAtributo
    extra = 1
    ordering = ('ordem',)

class TemplateComponenteInline(admin.TabularInline):
    model = TemplateComponente
    extra = 1

class FormulaTemplateInline(admin.StackedInline):
    model = FormulaTemplate
    extra = 1

class InstanciaAtributoInline(admin.TabularInline):
    model = InstanciaAtributo
    extra = 1
    readonly_fields = ('atributo',)

class InstanciaComponenteInline(admin.TabularInline):
    model = InstanciaComponente
    extra = 1
    readonly_fields = ('item_material', 'unidade', 'custo_unitario')

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

@admin.register(ItemMaterial)
class ItemMaterialAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'custo_unitario', 'unidade')
    search_fields = ('descricao',)

@admin.register(ProdutoTemplate)
class ProdutoTemplateAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria')
    list_filter = ('categoria',)
    search_fields = ('nome', 'descricao')
    inlines = [TemplateAtributoInline, TemplateComponenteInline, FormulaTemplateInline]

@admin.register(ProdutoInstancia)
class ProdutoInstanciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'template', 'quantidade')
    list_filter = ('template__categoria',)
    search_fields = ('codigo', 'template__nome')
    inlines = [
        InstanciaAtributoInline,
        InstanciaComponenteInline,
    ]
    readonly_fields = ('template',)

# Não é necessário registrar os modelos de "junção" diretamente
# pois eles são gerenciados através dos inlines.
# admin.site.register(TemplateAtributo)
# admin.site.register(TemplateComponente)
# admin.site.register(FormulaTemplate)
# admin.site.register(InstanciaAtributo)
# admin.site.register(InstanciaComponente)
