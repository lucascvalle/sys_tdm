"""
Views for the Estoque (Stock) application.

This module contains views for managing inventory, including stock adjustments,
listing categories, items, batches, and movements. It also provides API endpoints
for dynamic interactions.
"""

from __future__ import annotations
from typing import Any, Dict, List

from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, FormView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.http import JsonResponse, HttpRequest, HttpResponse

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from .models import CategoriaItem, ItemEstocavel, Lote, MovimentoEstoque
from .forms import AjusteEstoqueForm, LoteForm


class EstoqueHomeView(TemplateView):
    """
Renders the main home page for the stock module.
"""
    template_name = 'estoque/estoque_home.html'


class AjustarEstoqueView(LoginRequiredMixin, FormView):
    """
    Handles stock adjustments (positive or negative) for `ItemEstocavel`.

    Users can specify a new physical quantity, and the system calculates
    the difference, creating corresponding stock movements.
    """
    template_name = 'estoque/ajustar_estoque.html'
    form_class = AjusteEstoqueForm
    success_url = '/estoque/ajustar_estoque/' # Redirect to the same page after success

    def form_valid(self, form: AjusteEstoqueForm) -> HttpResponse:
        """
        Processes the valid form submission to perform stock adjustments.
        """
        item_estocavel = form.cleaned_data['item_estocavel']
        nova_quantidade_fisica = form.cleaned_data['nova_quantidade_fisica']
        justificativa = form.cleaned_data['justificativa']
        user = self.request.user

        with transaction.atomic():
            # Calculate current total stock for the item
            current_stock = sum(lote.quantidade_atual for lote in item_estocavel.lotes.all())

            difference = nova_quantidade_fisica - current_stock

            if difference == 0:
                messages.info(self.request, _("Nenhum ajuste necessário. A quantidade física já corresponde ao estoque."))
            else:
                if difference > 0: # Positive adjustment (entrada)
                    tipo_movimento = 'AJUSTE_P'
                    # Create a new dummy lote for positive adjustments if no existing lote can be used
                    # For simplicity, we'll assume a new lote is created for positive adjustments
                    # In a real scenario, you might want to add to an existing lote or a specific 'adjustment' lote
                    lote = Lote.objects.create(
                        item=item_estocavel,
                        quantidade_inicial=difference,
                        quantidade_atual=difference,
                        custo_unitario_compra=0 # Adjust cost as needed for positive adjustments
                    )
                    MovimentoEstoque.objects.create(
                        lote=lote,
                        quantidade=difference,
                        tipo=tipo_movimento,
                        responsavel=user,
                        observacao=justificativa # Add justificativa to observacao field if it exists
                    )
                    messages.success(self.request, _("Ajuste positivo de {difference} para {item_name} registrado.").format(difference=difference, item_name=item_estocavel.nome))

                else: # Negative adjustment (saída)
                    tipo_movimento = 'AJUSTE_N'
                    quantidade_a_ajustar = abs(difference)
                    
                    # Consume from lots (FIFO - First In, First Out)
                    lotes_disponiveis = item_estocavel.lotes.filter(quantidade_atual__gt=0).order_by('data_entrada')
                    
                    for lote in lotes_disponiveis:
                        if quantidade_a_ajustar <= 0: break

                        quantidade_do_lote = lote.quantidade_atual
                        quantidade_consumida = min(quantidade_a_ajustar, quantidade_do_lote)

                        lote.quantidade_atual -= quantidade_consumida
                        lote.save()

                        MovimentoEstoque.objects.create(
                            lote=lote,
                            quantidade=-quantidade_consumida, # Negative for salida
                            tipo=tipo_movimento,
                            responsavel=user,
                            observacao=justificativa # Add justificativa to observacao field if it exists
                        )
                        quantidade_a_ajustar -= quantidade_consumida
                    
                    if quantidade_a_ajustar > 0:
                        messages.warning(self.request, _("Ajuste negativo de {abs_difference} para {item_name} solicitado, mas não havia estoque suficiente para cobrir todo o ajuste. {remaining_qty} unidades restantes não ajustadas.").format(abs_difference=abs(difference), item_name=item_estocavel.nome, remaining_qty=quantidade_a_ajustar))
                    else:
                        messages.success(self.request, _("Ajuste negativo de {abs_difference} para {item_name} registrado.").format(abs_difference=abs(difference), item_name=item_estocavel.nome))

        return super().form_valid(form)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds `itens_estoque` (filtered) and `search_itens_estoque` to the context.
        """
        context = super().get_context_data(**kwargs)
        
        search_query = self.request.GET.get('search_itens_estoque', '')
        
        itens_estoque_queryset = ItemEstocavel.objects.all()
        if search_query:
            itens_estoque_queryset = itens_estoque_queryset.filter(nome__icontains=search_query)

        context['itens_estoque'] = []
        for item in itens_estoque_queryset:
            current_total_stock = sum(lote.quantidade_atual for lote in item.lotes.all())
            context['itens_estoque'].append({
                'item': item,
                'current_total_stock': current_total_stock
            })
        context['search_itens_estoque'] = search_query
        return context


class ListarCategoriasView(ListView):
    """
    Lists all `CategoriaItem` objects.
    """
    model = CategoriaItem
    template_name = 'estoque/listar_categorias.html'
    context_object_name = 'categorias'


class ListarItensEstocaveisView(ListView):
    """
    Lists all `ItemEstocavel` objects with filtering capabilities.

    Allows filtering by item name (description) and category.
    """
    model = ItemEstocavel
    template_name = 'estoque/listar_itens_estocaveis.html'
    context_object_name = 'itens'

    def get_queryset(self) -> models.QuerySet[ItemEstocavel]:
        """
        Returns the queryset of `ItemEstocavel` objects, filtered by GET parameters.
        """
        queryset = super().get_queryset()
        
        # Filtro por descrição
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(nome__icontains=query)

        # Filtro por categoria
        categoria_id = self.request.GET.get('categoria')
        if categoria_id:
            queryset = queryset.filter(categoria__id=categoria_id)
            
        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds `todas_categorias`, `selected_categoria`, and `search_query` to the context.
        """
        context = super().get_context_data(**kwargs)
        context['todas_categorias'] = CategoriaItem.objects.all()
        context['selected_categoria'] = self.request.GET.get('categoria', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class RegistrarEntradaView(CreateView):
    """
    Handles the registration of new `Lote` entries (stock receipts).
    """
    model = Lote
    form_class = LoteForm
    template_name = 'estoque/registrar_entrada.html'
    success_url = '/estoque/lotes/'


class ListarLotesView(ListView):
    """
    Lists all `Lote` objects, with optional filtering by `ItemEstocavel`.
    """
    model = Lote
    template_name = 'estoque/listar_lotes.html'
    context_object_name = 'lotes'

    def get_queryset(self) -> models.QuerySet[Lote]:
        """
        Returns the queryset of `Lote` objects, filtered by `item` GET parameter.
        """
        queryset = super().get_queryset()
        item_pk = self.request.GET.get('item')
        if item_pk:
            queryset = queryset.filter(item__pk=item_pk)
        return queryset

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds `selected_item_name` to the context if an item filter is applied.
        """
        context = super().get_context_data(**kwargs)
        item_pk = self.request.GET.get('item')
        if item_pk:
            try:
                selected_item = ItemEstocavel.objects.get(pk=item_pk)
                context['selected_item_name'] = selected_item.nome
            except ItemEstocavel.DoesNotExist:
                context['selected_item_name'] = ""
        else:
            context['selected_item_name'] = ""
        return context


class ListarMovimentacoesView(ListView):
    """
    Lists all `MovimentoEstoque` objects.
    """
    model = MovimentoEstoque
    template_name = 'estoque/listar_movimentacoes.html'
    context_object_name = 'movimentacoes'


# =============================================================================
# API Views
# =============================================================================

def api_listar_itens_estocaveis(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to return a list of `ItemEstocavel` objects in JSON.

    Used for autocompletion features (e.g., Select2).

    Args:
        request: The HttpRequest object. Supports GET parameter 'q' for search.

    Returns:
        A JsonResponse containing a list of items (id, nome).
    """
    query = request.GET.get('q', '')
    if query:
        itens = ItemEstocavel.objects.filter(nome__icontains=query).values('id', 'nome')[:10]
    else:
        itens = ItemEstocavel.objects.all().values('id', 'nome')[:10] # Retorna os primeiros 10 itens se a query estiver vazia
    return JsonResponse(list(itens), safe=False)


class CriarCategoriaView(CreateView):
    """
    Handles the creation of a new `CategoriaItem`.
    """
    model = CategoriaItem
    template_name = 'estoque/criar_categoria.html'
    fields = ['nome', 'parent']
    success_url = '/estoque/categorias/'


class CriarItemEstocavelView(CreateView):
    """
    Handles the creation of a new `ItemEstocavel`.
    """
    model = ItemEstocavel
    template_name = 'estoque/criar_item_estocavel.html'
    fields = '__all__'
    success_url = '/estoque/itens/'


class EditarItemEstocavelView(UpdateView):
    """
    Handles the editing of an existing `ItemEstocavel`.
    """
    model = ItemEstocavel
    template_name = 'estoque/editar_item_estocavel.html'
    fields = '__all__'
    success_url = '/estoque/itens/'


class ExcluirItemEstocavelView(DeleteView):
    """
    Handles the deletion of an `ItemEstocavel`.
    """
    model = ItemEstocavel
    template_name = 'estoque/excluir_item_estocavel.html'
    success_url = '/estoque/itens/'


class DetalhesItemEstocavelView(DetailView):
    """
    Displays the details of a specific `ItemEstocavel`.
    """
    model = ItemEstocavel
    template_name = 'estoque/detalhes_item_estocavel.html'
    context_object_name = 'item'