from django.urls import path
from .views import (
    EstoqueHomeView, 
    AjustarEstoqueView,
    ListarCategoriasView,
    ListarItensEstocaveisView,
    RegistrarEntradaView,
    ListarLotesView,
    ListarMovimentacoesView,
    CriarCategoriaView,
    CriarItemEstocavelView,
    EditarItemEstocavelView,
    ExcluirItemEstocavelView,
    DetalhesItemEstocavelView,
    api_listar_itens_estocaveis
)

app_name = 'estoque'

urlpatterns = [
    path('', EstoqueHomeView.as_view(), name='home'),
    path('ajustar_estoque/', AjustarEstoqueView.as_view(), name='ajustar_estoque'),
    path('categorias/', ListarCategoriasView.as_view(), name='listar_categorias'),
    path('categorias/criar/', CriarCategoriaView.as_view(), name='criar_categoria'),
    path('itens/', ListarItensEstocaveisView.as_view(), name='listar_itens_estocaveis'),
    path('itens/criar/', CriarItemEstocavelView.as_view(), name='criar_item'),
    path('itens/<int:pk>/editar/', EditarItemEstocavelView.as_view(), name='editar_item'),
    path('itens/<int:pk>/excluir/', ExcluirItemEstocavelView.as_view(), name='excluir_item'),
    path('itens/<int:pk>/', DetalhesItemEstocavelView.as_view(), name='detalhes_item'),
    path('entradas/registrar/', RegistrarEntradaView.as_view(), name='registrar_entrada'),
    path('lotes/', ListarLotesView.as_view(), name='listar_lotes'),
    path('movimentacoes/', ListarMovimentacoesView.as_view(), name='listar_movimentacoes'),
    path('api/itens/', api_listar_itens_estocaveis, name='api_listar_itens_estocaveis'),
]
