from django.contrib import admin
from .models import PostoTrabalho, FichaConsumoObra, ItemConsumido, SessaoTrabalho, Operador

@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


class ItemConsumidoInline(admin.TabularInline):
    model = ItemConsumido
    extra = 1  # Quantidade de formulários extras para exibir
    fields = ['data_consumo', 'item_estocavel', 'descricao_detalhada', 'quantidade', 'unidade']

@admin.register(FichaConsumoObra)
class FichaConsumoObraAdmin(admin.ModelAdmin):
    list_display = ('ref_obra', 'data_inicio', 'previsao_entrega', 'responsavel', 'status')
    list_filter = ('status', 'responsavel')
    search_fields = ('ref_obra',)
    inlines = [ItemConsumidoInline]

@admin.register(PostoTrabalho)
class PostoTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'custo_hora')
    search_fields = ('nome',)

@admin.register(SessaoTrabalho)
class SessaoTrabalhoAdmin(admin.ModelAdmin):
    list_display = ('posto_trabalho', 'operador', 'ficha_obra', 'hora_inicio', 'hora_saida')
    list_filter = ('posto_trabalho', 'operador', 'ficha_obra')
    search_fields = ('ficha_obra__ref_obra', 'operacao')

# O ItemConsumido é gerenciado através da FichaConsumoObra, mas podemos registrá-lo
# separadamente se for necessário acesso direto.
# admin.site.register(ItemConsumido)
