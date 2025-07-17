from django.urls import path
from . import views

urlpatterns = [
    path('', views.produtos_home, name='produtos_home'),
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/criar/', views.criar_categoria, name='criar_categoria'),
    path('templates/', views.listar_produtos_template, name='listar_produtos_template'),
    path('templates/criar/', views.criar_produto_template, name='criar_produto_template'),
    
    # TODO: Adicionar URLs para outros modelos e funcionalidades
]