from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_orcamentos, name='listar_orcamentos'),
    path('criar/', views.criar_orcamento, name='criar_orcamento'),
    path('<int:orcamento_id>/editar/', views.editar_orcamento, name='editar_orcamento'),
    path('<int:orcamento_id>/item/<int:item_id>/remover/', views.remover_item_orcamento, name='remover_item_orcamento'),
    path('<int:orcamento_id>/item/<int:item_id>/atualizar/', views.atualizar_item_orcamento, name='atualizar_item_orcamento'),
    path('<int:orcamento_id>/exportar/excel/', views.exportar_orcamento_excel, name='exportar_orcamento_excel'),
    path('<int:orcamento_id>/excluir/', views.excluir_orcamento, name='excluir_orcamento'),
    path('<int:orcamento_id>/versionar/', views.versionar_orcamento, name='versionar_orcamento'),
    # TODO: Adicionar URLs para salvar_nova_versao_orcamento, etc.
]