from django.urls import path
from . import views

urlpatterns = [
    path('', views.produtos_home, name='produtos_home'),
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/criar/', views.criar_categoria, name='criar_categoria'),
    path('templates/', views.listar_produtos_template, name='listar_produtos_template'),
    path('templates/criar/', views.criar_produto_template, name='criar_produto_template'),
    path('instancias/', views.listar_produto_instancias, name='listar_produto_instancias'),
    path('instancias/<int:instancia_id>/detalhes_json/', views.get_instancia_detalhes_json, name='get_instancia_detalhes_json'),
    
    
    # TODO: Adicionar URLs para outros modelos e funcionalidades
]