from django.shortcuts import render, redirect
from django.views.generic import TemplateView, FormView
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import ItemEstocavel, Lote, MovimentoEstoque
from .forms import AjusteEstoqueForm

class EstoqueHomeView(TemplateView):
    template_name = 'estoque/estoque_home.html'

class AjustarEstoqueView(LoginRequiredMixin, FormView):
    template_name = 'estoque/ajustar_estoque.html'
    form_class = AjusteEstoqueForm
    success_url = '/estoque/ajustar_estoque/' # Redirect to the same page after success

    def form_valid(self, form):
        item_estocavel = form.cleaned_data['item_estocavel']
        nova_quantidade_fisica = form.cleaned_data['nova_quantidade_fisica']
        justificativa = form.cleaned_data['justificativa']
        user = self.request.user

        with transaction.atomic():
            # Calculate current total stock for the item
            current_stock = sum(lote.quantidade_atual for lote in item_estocavel.lotes.all())

            difference = nova_quantidade_fisica - current_stock

            if difference == 0:
                messages.info(self.request, "Nenhum ajuste necessário. A quantidade física já corresponde ao estoque.")
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
                    messages.success(self.request, f"Ajuste positivo de {difference} para {item_estocavel.nome} registrado.")

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
                        messages.warning(self.request, f"Ajuste negativo de {abs(difference)} para {item_estocavel.nome} solicitado, mas não havia estoque suficiente para cobrir todo o ajuste. {quantidade_a_ajustar} unidades restantes não ajustadas.")
                    else:
                        messages.success(self.request, f"Ajuste negativo de {abs(difference)} para {item_estocavel.nome} registrado.")

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Optionally, add current stock levels to the context for display
        context['itens_estoque'] = []
        for item in ItemEstocavel.objects.all():
            current_total_stock = sum(lote.quantidade_atual for lote in item.lotes.all())
            context['itens_estoque'].append({
                'item': item,
                'current_total_stock': current_total_stock
            })
        return context
