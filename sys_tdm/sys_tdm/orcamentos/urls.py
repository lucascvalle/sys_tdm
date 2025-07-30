from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_orcamentos, name='listar_orcamentos'),
    path('criar/', views.criar_orcamento, name='criar_orcamento'),
    path('<int:orcamento_id>/editar/', views.editar_orcamento, name='editar_orcamento'),
    path('<int:orcamento_id>/item/<int:item_id>/remover/', views.remover_item_orcamento, name='remover_item_orcamento'),
    path('<int:orcamento_id>/item/<int:item_id>/atualizar/', views.atualizar_item_orcamento, name='atualizar_item_orcamento'),
    path('<int:orcamento_id>/exportar/excel/', views.exportar_orcamento_excel, name='exportar_orcamento_excel'),
    path('<int:orcamento_id>/exportar/ficha-producao/', views.exportar_ficha_producao, name='exportar_ficha_producao'),
    path('<int:orcamento_id>/excluir/', views.excluir_orcamento, name='excluir_orcamento'),
    path('<int:orcamento_id>/versionar/', views.versionar_orcamento, name='versionar_orcamento'),
    path('api/item/<int:item_id>/componentes/', views.get_item_components, name='get_item_components'),
    path('api/componente/<int:componente_id>/atualizar/', views.update_component, name='update_component'),
    path('api/item/<int:item_id>/total-component-cost/', views.get_item_total_component_cost, name='get_item_total_component_cost'),
    path('api/item/<int:item_id>/', views.get_item_details, name='get_item_details'),
    path('api/item/<int:item_id>/atualizar-detalhes/', views.update_item_details, name='update_item_details'),
    path('api/item/<int:item_id>/row-html/', views.get_item_row_html, name='get_item_row_html'),
    path('api/item/<int:item_id>/update-components-and-attributes/', views.update_item_components_and_attributes, name='update_item_components_and_attributes'),
    path('api/item/<int:item_id>/update-components-and-attributes/', views.update_item_components_and_attributes, name='update_item_components_and_attributes'),
    # NOVAS ROTAS PARA OS DROPDOWNS
    path('api/categoria/<int:categoria_id>/templates/', views.get_templates_for_categoria, name='get_templates_for_categoria'),
    path('api/template/<int:template_id>/configuracoes/', views.get_configuracoes_for_template, name='get_configuracoes_for_template'),
    path('api/configuracao/<int:configuracao_id>/atributos/', views.get_atributos_for_configuracao, name='get_atributos_for_configuracao'),
]