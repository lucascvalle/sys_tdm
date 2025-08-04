"""
Admin configuration for the Consumos (Consumption) application.

This module registers the consumption-related models with the Django admin site
and customizes their appearance and behavior.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    PostoTrabalho, FichaConsumoObra, ItemConsumido, Operador, SessaoTrabalho
)


@admin.register(PostoTrabalho)
class PostoTrabalhoAdmin(admin.ModelAdmin):
    """
    Admin options for the `PostoTrabalho` model.
    """
    list_display = ('nome', 'custo_hora')
    search_fields = ('nome',)


@admin.register(FichaConsumoObra)
class FichaConsumoObraAdmin(admin.ModelAdmin):
    """
    Admin options for the `FichaConsumoObra` model.
    """
    list_display = ('ref_obra', 'data_inicio', 'previsao_entrega', 'responsavel', 'status')
    search_fields = ('ref_obra', 'responsavel__username')
    list_filter = ('status', 'data_inicio', 'previsao_entrega')
    raw_id_fields = ('responsavel',) # Use raw_id_fields for ForeignKey to User for better performance with many users


@admin.register(ItemConsumido)
class ItemConsumidoAdmin(admin.ModelAdmin):
    """
    Admin options for the `ItemConsumido` model.
    """
    list_display = ('ficha_obra', 'data_consumo', 'item_estocavel', 'quantidade', 'unidade')
    search_fields = ('ficha_obra__ref_obra', 'item_estocavel__nome', 'descricao_detalhada')
    list_filter = ('data_consumo', 'ficha_obra', 'item_estocavel__categoria')
    raw_id_fields = ('ficha_obra', 'item_estocavel')


@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    """
    Admin options for the `Operador` model.
    """
    list_display = ('nome',)
    search_fields = ('nome',)


@admin.register(SessaoTrabalho)
class SessaoTrabalhoAdmin(admin.ModelAdmin):
    """
    Admin options for the `SessaoTrabalho` model.
    """
    list_display = ('posto_trabalho', 'operador', 'ficha_obra', 'hora_inicio', 'hora_saida')
    search_fields = ('posto_trabalho__nome', 'operador__nome', 'ficha_obra__ref_obra', 'operacao')
    list_filter = ('posto_trabalho', 'operador', 'ficha_obra', 'hora_inicio', 'hora_saida')
    raw_id_fields = ('posto_trabalho', 'operador', 'ficha_obra')