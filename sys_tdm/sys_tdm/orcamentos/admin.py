from django.contrib import admin
from .models import Orcamento, ItemOrcamento

class ItemOrcamentoInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0  # Não mostrar itens extras por padrão
    readonly_fields = ('instancia', 'preco_unitario', 'quantidade', 'total')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ('codigo_legado', 'versao', 'usuario', 'criado_em', 'atualizado_em')
    list_filter = ('usuario', 'criado_em')
    search_fields = ('codigo_legado',)
    inlines = [ItemOrcamentoInline]
    readonly_fields = ('criado_em', 'atualizado_em', 'versao_base')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('itens__instancia__template')