from django.contrib import admin
from .models import CategoriaItem, ItemEstocavel, Lote, MovimentoEstoque

@admin.register(CategoriaItem)
class CategoriaItemAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_categoria', 'parent')
    search_fields = ('nome', 'codigo_categoria')
    list_filter = ('parent',)

@admin.register(ItemEstocavel)
class ItemEstocavelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_interno_gerado', 'codigo_sku_fornecedor', 'categoria', 'unidade_medida')
    search_fields = ('nome', 'codigo_interno_gerado', 'codigo_sku_fornecedor', 'descricao')
    list_filter = ('categoria', 'unidade_medida')
    ordering = ('categoria', 'codigo_interno_item')
    readonly_fields = ('codigo_interno_item', 'codigo_interno_gerado')

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'item', 'quantidade_atual', 'custo_unitario_compra', 'data_entrada')
    search_fields = ('item__nome', 'item__codigo_sku_fornecedor', 'item__codigo_interno_gerado')
    list_filter = ('data_entrada', 'item__categoria')
    # Tornar campos que são preenchidos automaticamente como apenas de leitura
    readonly_fields = ('quantidade_atual',)

    def save_model(self, request, obj, form, change):
        """
        Sobrescreve o método save para criar o movimento de entrada inicial.
        """
        # Se for um novo lote (não uma alteração)
        if not obj.pk:
            # Define a quantidade atual e salva o lote primeiro para obter um ID
            obj.quantidade_atual = obj.quantidade_inicial
            super().save_model(request, obj, form, change)
            
            # Cria o movimento de estoque de entrada inicial
            MovimentoEstoque.objects.create(
                lote=obj,
                quantidade=obj.quantidade_inicial,
                tipo='ENTRADA',
                responsavel=request.user
            )
        else:
            super().save_model(request, obj, form, change)

@admin.register(MovimentoEstoque)
class MovimentoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'lote', 'tipo', 'quantidade', 'responsavel')
    search_fields = ('lote__item__nome', 'lote__item__codigo_sku_fornecedor', 'responsavel__username')
    list_filter = ('tipo', 'timestamp')
    readonly_fields = ('lote', 'quantidade', 'tipo', 'responsavel', 'origem_consumo', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False