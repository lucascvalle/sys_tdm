from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormMixin
from django.db.models import Sum
from .models import FichaConsumoObra, SessaoTrabalho, PostoTrabalho, Operador, ItemConsumido
from .forms import FichaConsumoObraForm, SessaoTrabalhoForm, PostoTrabalhoForm, OperadorForm, ItemConsumidoForm, MaterialConsumptionReportFilterForm, MachineUtilizationReportFilterForm
from .excel_utils import exportar_consumo_material_excel, exportar_utilizacao_maquina_excel

class ConsumosHomeView(TemplateView):
    template_name = 'consumos/consumos_home.html'

# Views para FichaConsumoObra
class FichaConsumoObraListView(ListView):
    model = FichaConsumoObra
    template_name = 'consumos/ficha_consumo_list.html'
    context_object_name = 'fichas'

class FichaConsumoObraCreateView(CreateView):
    model = FichaConsumoObra
    form_class = FichaConsumoObraForm
    template_name = 'consumos/ficha_consumo_form.html'
    success_url = reverse_lazy('consumos:ficha_consumo_list')

class FichaConsumoObraDetailView(FormMixin, DetailView):
    model = FichaConsumoObra
    template_name = 'consumos/ficha_consumo_detail.html'
    context_object_name = 'ficha'
    form_class = ItemConsumidoForm

    def get_success_url(self):
        return reverse_lazy('consumos:ficha_consumo_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.get_form()
        context['itens_consumidos'] = self.object.itens_consumidos.all()
        context['sessoes_trabalho_relacionadas'] = self.object.sessoes_trabalho_relacionadas.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        item_consumido = form.save(commit=False)
        item_consumido.ficha_obra = self.object
        item_consumido.save()
        return super().form_valid(form)

class FichaConsumoObraUpdateView(UpdateView):
    model = FichaConsumoObra
    form_class = FichaConsumoObraForm
    template_name = 'consumos/ficha_consumo_form.html'
    success_url = reverse_lazy('consumos:ficha_consumo_list')

# Views para ItemConsumido
class ItemConsumidoDeleteView(DeleteView):
    model = ItemConsumido
    template_name = 'consumos/item_consumido_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('consumos:ficha_consumo_detail', kwargs={'pk': self.object.ficha_obra.pk})

# Views para SessaoTrabalho
class SessaoTrabalhoListView(ListView):
    model = SessaoTrabalho
    template_name = 'consumos/sessao_trabalho_list.html'
    context_object_name = 'sessoes'

class SessaoTrabalhoCreateView(CreateView):
    model = SessaoTrabalho
    form_class = SessaoTrabalhoForm
    template_name = 'consumos/sessao_trabalho_form.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')

class SessaoTrabalhoUpdateView(UpdateView):
    model = SessaoTrabalho
    form_class = SessaoTrabalhoForm
    template_name = 'consumos/sessao_trabalho_form.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')

class SessaoTrabalhoDeleteView(DeleteView):
    model = SessaoTrabalho
    template_name = 'consumos/sessao_trabalho_confirm_delete.html'
    success_url = reverse_lazy('consumos:sessao_trabalho_list')

# Views para PostoTrabalho
class PostoTrabalhoListView(ListView):
    model = PostoTrabalho
    template_name = 'consumos/posto_trabalho_list.html'
    context_object_name = 'postos'

class PostoTrabalhoCreateView(CreateView):
    model = PostoTrabalho
    form_class = PostoTrabalhoForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')

class PostoTrabalhoUpdateView(UpdateView):
    model = PostoTrabalho
    form_class = PostoTrabalhoForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')

class PostoTrabalhoDeleteView(DeleteView):
    model = PostoTrabalho
    template_name = 'consumos/generic_confirm_delete.html'
    success_url = reverse_lazy('consumos:posto_trabalho_list')

# Views para Operador
class OperadorListView(ListView):
    model = Operador
    template_name = 'consumos/operador_list.html'
    context_object_name = 'operadores'

class OperadorCreateView(CreateView):
    model = Operador
    form_class = OperadorForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:operador_list')

class OperadorUpdateView(UpdateView):
    model = Operador
    form_class = OperadorForm
    template_name = 'consumos/generic_form.html'
    success_url = reverse_lazy('consumos:operador_list')

class OperadorDeleteView(DeleteView):
    model = Operador
    template_name = 'consumos/generic_confirm_delete.html'
    success_url = reverse_lazy('consumos:operador_list')

# Views para Relatórios
class MaterialConsumptionReportView(ListView):
    template_name = 'consumos/material_consumption_report.html'
    context_object_name = 'consumos_agregados'

    def get_queryset(self):
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
            'componente__nome', 'unidade'
        ).annotate(
            total_quantidade=Sum('quantidade')
        ).order_by('componente__nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = MaterialConsumptionReportFilterForm(self.request.GET)
        return context

def exportar_material_consumption_excel(request):
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
        'componente__nome', 'descricao_detalhada', 'unidade'
    ).annotate(
        total_quantidade=Sum('quantidade')
    ).order_by('componente__nome', 'descricao_detalhada')

    return exportar_consumo_material_excel(request, consumos_agregados, filtros)


class MachineUtilizationReportView(ListView):
    template_name = 'consumos/machine_utilization_report.html'
    context_object_name = 'sessoes_agregadas'

    def get_queryset(self):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = MachineUtilizationReportFilterForm(self.request.GET)
        return context

def exportar_machine_utilization_excel(request):
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
