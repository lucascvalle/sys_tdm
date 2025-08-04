from django.urls import path
from . import views

app_name = 'consumos'

urlpatterns = [
    path('', views.ConsumosHomeView.as_view(), name='home'),
    # Fichas de Consumo de Obra
    path('fichas/', views.FichaConsumoObraListView.as_view(), name='ficha_consumo_list'),
    path('fichas/nova/', views.FichaConsumoObraCreateView.as_view(), name='ficha_consumo_create'),
    path('fichas/<int:pk>/', views.FichaConsumoObraDetailView.as_view(), name='ficha_consumo_detail'),
    path('fichas/<int:pk>/editar/', views.FichaConsumoObraUpdateView.as_view(), name='ficha_consumo_update'),

    # Itens Consumidos
    path('item/<int:pk>/excluir/', views.ItemConsumidoDeleteView.as_view(), name='item_consumido_delete'),

    # Sessões de Trabalho
    path('sessoes/', views.SessaoTrabalhoListView.as_view(), name='sessao_trabalho_list'),
    path('sessoes/nova/', views.SessaoTrabalhoCreateView.as_view(), name='sessao_trabalho_create'),
    path('sessoes/<int:pk>/editar/', views.SessaoTrabalhoUpdateView.as_view(), name='sessao_trabalho_update'),
    path('sessoes/<int:pk>/excluir/', views.SessaoTrabalhoDeleteView.as_view(), name='sessao_trabalho_delete'),

    # Gerenciamento de Postos de Trabalho e Operadores
    path('postos/', views.PostoTrabalhoListView.as_view(), name='posto_trabalho_list'),
    path('postos/novo/', views.PostoTrabalhoCreateView.as_view(), name='posto_trabalho_create'),
    path('postos/<int:pk>/editar/', views.PostoTrabalhoUpdateView.as_view(), name='posto_trabalho_update'),
    path('postos/<int:pk>/excluir/', views.PostoTrabalhoDeleteView.as_view(), name='posto_trabalho_delete'),
    path('operadores/', views.OperadorListView.as_view(), name='operador_list'),
    path('operadores/novo/', views.OperadorCreateView.as_view(), name='operador_create'),
    path('operadores/<int:pk>/editar/', views.OperadorUpdateView.as_view(), name='operador_update'),
    path('operadores/<int:pk>/excluir/', views.OperadorDeleteView.as_view(), name='operador_delete'),

    # API Endpoints para a Dashboard
    path('api/obra/<int:obra_id>/detalhes/', views.get_consumos_por_obra_api, name='api_get_consumos_por_obra'),

    # Relatórios
    path('relatorios/kpis/', views.kpi_dashboard, name='kpi_dashboard'),
    path('relatorios/consumo-material/', views.MaterialConsumptionReportView.as_view(), name='material_consumption_report'),
    path('relatorios/consumo-material/exportar/', views.exportar_material_consumption_excel, name='exportar_material_consumption_excel'),
    path('relatorios/consumo-material/exportar-modelo-impressao/', views.exportar_material_consumption_print_model, name='exportar_material_consumption_print_model'),
    path('relatorios/utilizacao-maquina/', views.MachineUtilizationReportView.as_view(), name='machine_utilization_report'),
    path('relatorios/utilizacao-maquina/exportar/', views.exportar_machine_utilization_excel, name='exportar_machine_utilization_excel'),
    path('relatorios/utilizacao-maquina/exportar-modelo-impressao/', views.exportar_machine_utilization_print_model, name='exportar_machine_utilization_print_model'),
    path('api/fichas-obra/', views.api_listar_fichas_obra, name='api_listar_fichas_obra'),
]
