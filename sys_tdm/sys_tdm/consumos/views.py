"""
Views for the Consumos (Consumption) application.

This module handles the management of work order sheets (FichaConsumoObra),
material consumption records (ItemConsumido), work sessions (SessaoTrabalho),
workstations (PostoTrabalho), and operators (Operador). It also provides
KPI dashboards and reporting functionalities.
"""

from __future__ import annotations
from datetime import date, timedelta
from typing import Any, Dict, List

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Avg, Count, Q
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView, CreateView, DetailView, UpdateView, DeleteView, TemplateView
)
from django.views.generic.edit import FormMixin
from django.utils.translation import gettext_lazy as _

from .models import (
    FichaConsumoObra, SessaoTrabalho, PostoTrabalho, Operador, ItemConsumido
)
from .forms import (
    FichaConsumoObraForm, SessaoTrabalhoForm, PostoTrabalhoForm, OperadorForm,
    ItemConsumidoForm, MaterialConsumptionReportFilterForm,
    MachineUtilizationReportFilterForm
)
from .excel_utils import (
    exportar_consumo_material_excel, exportar_utilizacao_maquina_excel
)


# =============================================================================
# HTML Rendering Views
# =============================================================================

@login_required
def kpi_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Renders the KPI dashboard for consumption and production metrics.

    Displays aggregated data such as total production time, time per workstation
    and operator, and average time per operation.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse object rendering the KPI dashboard.
    """
    sessoes_completas = SessaoTrabalho.objects.filter(hora_saida__isnull=False)

    # KPI 1: Tempo de Produção Total (Agregado)
    tempo_total_producao_delta = sessoes_completas.aggregate(
        total_duracao=Sum(F('hora_saida') - F('hora_inicio'))
    )['total_duracao'] or timedelta(0)
    tempo_total_producao_horas = tempo_total_producao_delta.total_seconds() / 3600

    # KPI 2: Tempo de Produção por Posto de Trabalho
    tempo_por_posto = PostoTrabalho.objects.annotate(
        total_producao=Coalesce(Sum(F('sessoes_trabalho__hora_saida') - F('sessoes_trabalho__hora_inicio'), filter=Q(sessoes_trabalho__hora_saida__isnull=False)), timedelta(0))
    ).order_by('-total_producao')
    for posto in tempo_por_posto:
        posto.total_producao_horas = posto.total_producao.total_seconds() / 3600

    # KPI 3: Tempo de Produção por Operador
    tempo_por_operador = Operador.objects.annotate(
        total_producao=Coalesce(Sum(F('sessoes_trabalho__hora_saida') - F('sessoes_trabalho__hora_inicio'), filter=Q(sessoes_trabalho__hora_saida__isnull=False)), timedelta(0))
    ).order_by('-total_producao')
    for operador_obj in tempo_por_operador:
        operador_obj.total_producao_horas = operador_obj.total_producao.total_seconds() / 3600

    # KPI 4: Tempo Médio por Operação
    tempo_medio_por_operacao = sessoes_completas.values('operacao').annotate(
        duracao_media=Avg(F('hora_saida') - F('hora_inicio')),
        num_execucoes=Count('id')
    ).order_by('-duracao_media')
    for operacao in tempo_medio_por_operacao:
        if operacao['duracao_media']:
            operacao['duracao_media_minutos'] = operacao['duracao_media'].total_seconds() / 60
        else:
            operacao['duracao_media_minutos'] = 0

    # Obter todas as fichas de obra para o dropdown
    todas_as_obras = FichaConsumoObra.objects.all().order_by('-data_inicio')

    context = {
        'tempo_total_producao_horas': tempo_total_producao_horas,
        'tempo_por_posto': tempo_por_posto,
        'tempo_por_operador': tempo_por_operador,
        'tempo_medio_por_operacao': tempo_medio_por_operacao,
        'todas_as_obras': todas_as_obras,
    }
    return render(request, 'consumos/kpi_dashboard.html', context)


class ConsumosHomeView(TemplateView):
    """
Renders the main home page for the consumption module.
"""
    template_name = 'consumos/consumos_home.html'


# Views para FichaConsumoObra
class FichaConsumoObraListView(ListView):
    """
    Lists all `FichaConsumoObra` objects.
    """
    model = FichaConsumoObra
    template_name = 'consumos/ficha_consumo_list.html'
    context_object_name = 'fichas'


class FichaConsumoObraCreateView(CreateView):
    """
    Handles the creation of a new `FichaConsumoObra`.
    """
    model = FichaConsumoObra
    form_class = FichaConsumoObraForm
    template_name = 'consumos/ficha_consumo_form.html'
    success_url = reverse_lazy('consumos:ficha_consumo_list')


class FichaConsumoObraDetailView(FormMixin, DetailView):
    """
    Displays the details of a specific `FichaConsumoObra`.

    Also handles the creation of `ItemConsumido` and displays related work sessions.
    """
    model = FichaConsumoObra
    template_name = 'consumos/ficha_consumo_detail.html'
    context_object_name = 'ficha'
    form_class = ItemConsumidoForm

    def get_success_url(self) -> str:
        """
        Returns the URL to redirect to after a successful form submission.
        """
        return reverse_lazy('consumos:ficha_consumo_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds the form for `ItemConsumido`, consumed items, and related work sessions to the context.
        """
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['itens_consumidos'] = self.object.itens_consumidos.all()
        context['sessoes_trabalho_relacionadas'] = self.object.sessoes_trabalho_relacionadas.all()
        return context

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Handles POST requests for adding `ItemConsumido`.
        """
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form: ItemConsumidoForm) -> HttpResponse:
        """
        Saves the `ItemConsumido` and associates it with the current `FichaConsumoObra`.
        """
        item_consumido = form.save(commit=False)
        item_consumido.ficha_obra = self.object
        item_consumido.save()
        return super().form_valid(form)


class FichaConsumoObraUpdateView(UpdateView):
    """
    Handles the updating of an existing `FichaConsumoObra`.
    """
    model = FichaConsumoObra
    form_class = FichaConsumoObraForm
    template_name = 'consumos/ficha_consumo_form.html'
    success_url = reverse_lazy('consumos:ficha_consumo_list')


# Views para ItemConsumido
class ItemConsumidoDeleteView(DeleteView):
    """
    Handles the deletion of an `ItemConsumido`.
    """
    model = ItemConsumido
    template_name = 'consumos/item_consumido_confirm_delete.html'

    def get_success_url(self) -> str:
        """
        Returns the URL to redirect to after a successful deletion.
        """
        return reverse_lazy('consumos:ficha_consumo_detail', kwargs={'pk': self.object.ficha_obra.pk})


# Views para SessaoTrabalho
class SessaoTrabalhoListView(ListView):
    """
    Lists all `SessaoTrabalho` objects.
    """
    model = SessaoTrabalho
    template_name = 'consumos/sessao_trabalho_list.html'
    context_object_name = 'sessoes'


class SessaoTrabalhoCreateView(CreateView):
    """
    Handles the creation of a new `SessaoTrabalho`.
    """
    model = SessaoTrabalho
    form_class = SessaoTrabalhoForm
    template_name = 'consumos/sessao_trabalho_form.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')


class SessaoTrabalhoUpdateView(UpdateView):
    """
    Handles the updating of an existing `SessaoTrabalho`.
    """
    model = SessaoTrabalho
    form_class = SessaoTrabalhoForm
    template_name = 'consumos/sessao_trabalho_form.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')


class SessaoTrabalhoDeleteView(DeleteView):
    """
    Handles the deletion of a `SessaoTrabalho`.
    """
    model = SessaoTrabalho
    template_name = 'consumos/sessao_trabalho_confirm_delete.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')


# Views para PostoTrabalho
class PostoTrabalhoListView(ListView):
    """
    Lists all `PostoTrabalho` objects.
    """
    model = PostoTrabalho
    template_name = 'consumos/posto_trabalho_list.html'
    context_object_name = 'postos'


class PostoTrabalhoCreateView(CreateView):
    """
    Handles the creation of a new `PostoTrabalho`.
    """
    model = PostoTrabalho
    form_class = PostoTrabalhoForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')


class PostoTrabalhoUpdateView(UpdateView):
    """
    Handles the updating of an existing `PostoTrabalho`.
    """
    model = PostoTrabalho
    form_class = PostoTrabalhoForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')


class PostoTrabalhoDeleteView(DeleteView):
    """
    Handles the deletion of a `PostoTrabalho`.
    """
    model = PostoTrabalho
    template_name = 'consumos/generic_confirm_delete.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')


# Views para Operador
class OperadorListView(ListView):
    """
    Lists all `Operador` objects.
    """
    model = Operador
    template_name = 'consumos/operador_list.html'
    context_object_name = 'operadores'


class OperadorCreateView(CreateView):
    """
    Handles the creation of a new `Operador`.
    """
    model = Operador
    form_class = OperadorForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:operador_list')


class OperadorUpdateView(UpdateView):
    """
    Handles the updating of an existing `Operador`.
    """
    model = Operador
    form_class = OperadorForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:operador_list')


class OperadorDeleteView(DeleteView):
    """
    Handles the deletion of an `Operador`.
    """
    model = Operador
    template_name = 'consumos/generic_confirm_delete.html'
    success_url = reverse_lazy('consumos:operador_list')


# Views para Relatórios
class MaterialConsumptionReportView(ListView):
    """
    Displays a report of material consumption, with filtering options.
    """
    template_name = 'consumos/material_consumption_report.html'
    context_object_name = 'consumos_agregados'

    def get_queryset(self) -> models.QuerySet[ItemConsumido]:
        """
        Returns the queryset of `ItemConsumido` objects, filtered by GET parameters
        and aggregated by item and unit.
        """
        queryset = ItemConsumido.objects.all()
        form = MaterialConsumptionReportFilterForm(self.request.GET)

        if form.is_valid():
            data_inicio = form.cleaned_data.get('data_inicio')
            data_fim = form.cleaned_data.get('data_fim')
            componente = form.cleaned_data.get('componente')
            ficha_obra = form.cleaned_data.get('ficha_obra')

            if data_inicio:
                queryset = queryset.filter(data_consumo__gte=data_inicio)
            if data_fim:
                queryset = queryset.filter(data_consumo__lte=data_fim)
            if componente:
                queryset = queryset.filter(componente=componente)
            if ficha_obra:
                queryset = queryset.filter(ficha_obra=ficha_obra)

        # Agrega os consumos por componente e unidade
        return queryset.values(
            'item_estocavel__nome', 'unidade'
        ).annotate(
            total_quantidade=Sum('quantidade')
        ).order_by('item_estocavel__nome')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds the filter form to the context.
        """
        context = super().get_context_data(**kwargs)
        context['filter_form'] = MaterialConsumptionReportFilterForm(self.request.GET)
        return context


def exportar_material_consumption_excel(request: HttpRequest) -> HttpResponse:
    """
    Exports the material consumption report to an Excel file.

    Args:
        request: The HttpRequest object, containing filter parameters.

    Returns:
        An HttpResponse with the Excel file attachment.
    """
    form = MaterialConsumptionReportFilterForm(request.GET)
    queryset = ItemConsumido.objects.all()
    filtros = {}

    if form.is_valid():
        data_inicio = form.cleaned_data.get('data_inicio')
        data_fim = form.cleaned_data.get('data_fim')
        componente = form.cleaned_data.get('componente')
        ficha_obra = form.cleaned_data.get('ficha_obra')

        if data_inicio:
            queryset = queryset.filter(data_consumo__gte=data_inicio)
            filtros['data_inicio'] = data_inicio.strftime('%d/%m/%Y')
        if data_fim:
            queryset = queryset.filter(data_consumo__lte=data_fim)
            filtros['data_fim'] = data_fim.strftime('%d/%m/%Y')
        if componente:
            queryset = queryset.filter(componente=componente)
            filtros['componente'] = componente.nome
        if ficha_obra:
            queryset = queryset.filter(ficha_obra=ficha_obra)
            filtros['ref_obra'] = ficha_obra.ref_obra
            filtros['data_inicio_ficha'] = ficha_obra.data_inicio.strftime('%d/%m/%Y')
            filtros['previsao_entrega_ficha'] = ficha_obra.previsao_entrega.strftime('%d/%m/%Y')

    consumos_agregados = queryset.values(
        'item_estocavel__nome', 'descricao_detalhada', 'unidade'
    ).annotate(
        total_quantidade=Sum('quantidade')
    ).order_by('item_estocavel__nome', 'descricao_detalhada')

    return exportar_consumo_material_excel(request, consumos_agregados, filtros)


def exportar_material_consumption_print_model(request: HttpRequest) -> HttpResponse:
    """
    Serves the Excel template for printing material consumption reports.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse with the Excel template file attachment.
    """
    template_path = settings.BASE_DIR / 'static' / 'excel_templates' / 'modelo_impressao_consumo_material.xlsx'
    try:
        with open(template_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="modelo_impressao_consumo_material.xlsx"'
            return response
    except FileNotFoundError:
        messages.error(request, _("O arquivo de template Excel (modelo_impressao_consumo_material.xlsx) não foi encontrado."))
        return redirect('consumos:material_consumption_report')
    except Exception as e:
        messages.error(request, _("Erro ao exportar modelo de impressão: {error}").format(error=e))
        return redirect('consumos:material_consumption_report')


class MachineUtilizationReportView(ListView):
    """
    Displays a report of machine utilization, with filtering options.
    """
    template_name = 'consumos/machine_utilization_report.html'
    context_object_name = 'sessoes_agregadas'

    def get_queryset(self) -> models.QuerySet[SessaoTrabalho]:
        """
        Returns the queryset of `SessaoTrabalho` objects, filtered by GET parameters.
        """
        queryset = SessaoTrabalho.objects.all()
        form = MachineUtilizationReportFilterForm(self.request.GET)

        if form.is_valid():
            posto_trabalho = form.cleaned_data.get('posto_trabalho')
            operador = form.cleaned_data.get('operador')
            ficha_obra = form.cleaned_data.get('ficha_obra')
            data = form.cleaned_data.get('data')

            if posto_trabalho:
                queryset = queryset.filter(posto_trabalho=posto_trabalho)
            if operador:
                queryset = queryset.filter(operador=operador)
            if ficha_obra:
                queryset = queryset.filter(ficha_obra=ficha_obra)
            if data:
                queryset = queryset.filter(hora_inicio__date=data)

        return queryset.order_by('hora_inicio')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Adds the filter form to the context.
        """
        context = super().get_context_data(**kwargs)
        context['filter_form'] = MachineUtilizationReportFilterForm(self.request.GET)
        return context


def exportar_machine_utilization_excel(request: HttpRequest) -> HttpResponse:
    """
    Exports the machine utilization report to an Excel file.

    Args:
        request: The HttpRequest object, containing filter parameters.

    Returns:
        An HttpResponse with the Excel file attachment.
    """
    form = MachineUtilizationReportFilterForm(request.GET)
    queryset = SessaoTrabalho.objects.all()
    filtros = {}

    if form.is_valid():
        posto_trabalho = form.cleaned_data.get('posto_trabalho')
        operador = form.cleaned_data.get('operador')
        ficha_obra = form.cleaned_data.get('ficha_obra')
        data = form.cleaned_data.get('data')

        if posto_trabalho:
            queryset = queryset.filter(posto_trabalho=posto_trabalho)
            filtros['posto_trabalho'] = posto_trabalho.nome
        if operador:
            queryset = queryset.filter(operador=operador)
            filtros['operador'] = operador.nome
        if ficha_obra:
            queryset = queryset.filter(ficha_obra=ficha_obra)
            filtros['ficha_obra'] = ficha_obra.ref_obra
        if data:
            queryset = queryset.filter(hora_inicio__date=data)
            filtros['data'] = data.strftime('%d/%m/%Y')

    return exportar_utilizacao_maquina_excel(request, queryset, filtros)


def exportar_machine_utilization_print_model(request: HttpRequest) -> HttpResponse:
    """
    Serves the Excel template for printing machine utilization reports.

    Args:
        request: The HttpRequest object.

    Returns:
        An HttpResponse with the Excel template file attachment.
    """
    template_path = settings.BASE_DIR / 'static' / 'excel_templates' / 'modelo_impressao_ficha_postos_maquinas.xlsx'
    try:
        with open(template_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="modelo_impressao_ficha_postos_maquinas.xlsx"'
            return response
    except FileNotFoundError:
        messages.error(request, _("O arquivo de template Excel (modelo_impressao_ficha_postos_maquinas.xlsx) não foi encontrado."))
        return redirect('consumos:machine_utilization_report')
    except Exception as e:
        messages.error(request, _("Erro ao exportar modelo de impressão: {error}").format(error=e))
        return redirect('consumos:machine_utilization_report')


# =============================================================================
# API Views
# =============================================================================

@login_required
def get_consumos_por_obra_api(request: HttpRequest, obra_id: int) -> JsonResponse:
    """
    API endpoint to return consumption details for a specific work order.

    Args:
        request: The HttpRequest object.
        obra_id: The primary key of the `FichaConsumoObra`.

    Returns:
        A JsonResponse containing the work order's consumption data.
    """
    try:
        ficha_obra = get_object_or_404(FichaConsumoObra, pk=obra_id)
        itens_consumidos = ItemConsumido.objects.filter(ficha_obra=ficha_obra).select_related('item_estocavel')

        data = {
            'ref_obra': ficha_obra.ref_obra,
            'previsao_entrega': ficha_obra.previsao_entrega.strftime('%d/%m/%Y') if ficha_obra.previsao_entrega else 'N/A',
            'itens': [
                {
                    'componente': item.item_estocavel.nome if item.item_estocavel else _('Item sem componente associado'),
                    'quantidade': item.quantidade,
                    'unidade': item.unidade,
                }
                for item in itens_consumidos
            ]
        }
        return JsonResponse(data)
    except FichaConsumoObra.DoesNotExist:
        return JsonResponse({'error': _('Obra não encontrada.')}, status=404)


@login_required
def api_listar_fichas_obra(request: HttpRequest) -> JsonResponse:
    """
    API endpoint to return a list of `FichaConsumoObra` objects in JSON.

    Used for autocompletion features (e.g., Select2).

    Args:
        request: The HttpRequest object. Supports GET parameter 'q' for search.

    Returns:
        A JsonResponse containing a list of work order sheets (id, ref_obra).
    """
    query = request.GET.get('q', '')
    if query:
        fichas = FichaConsumoObra.objects.filter(ref_obra__icontains=query).values('id', 'ref_obra')[:10]
    else:
        fichas = FichaConsumoObra.objects.all().values('id', 'ref_obra')[:10] # Retorna os primeiros 10 se a query estiver vazia
    return JsonResponse(list(fichas), safe=False)
