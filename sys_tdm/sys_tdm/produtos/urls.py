from django.urls import path
from . import views

urlpatterns = [
    path('', views.produtos_home, name='produtos_home'),
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/criar/', views.criar_categoria, name='criar_categoria'),
    path('templates/', views.listar_produtos_template, name='listar_produtos_template'),
    path('templates/criar/', views.criar_produto_template, name='criar_produto_template'),
    path('instancias/', views.listar_produto_instancias, name='listar_produto_instancias'),

    # URLs para ProdutoConfiguracao
    path('configuracoes/', views.listar_produto_configuracoes, name='listar_produto_configuracoes'),
    path('configuracoes/criar/', views.criar_produto_configuracao, name='criar_produto_configuracao'),
    path('configuracoes/<int:pk>/editar/', views.editar_produto_configuracao, name='editar_produto_configuracao'),
    path('configuracoes/<int:pk>/excluir/', views.excluir_produto_configuracao, name='excluir_produto_configuracao'),

    # API URLs
    path('api/template/<int:template_id>/componentes/', views.get_template_components_by_template, name='api_get_template_components_by_template'),
    path('api/componentes/', views.get_all_components, name='api_get_all_components'),

    # TODO: Adicionar URLs para outros modelos e funcionalidades
]