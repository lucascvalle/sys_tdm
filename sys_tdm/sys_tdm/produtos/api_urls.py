from django.urls import path
from . import views

app_name = 'produtos_api'

urlpatterns = [
    path('categoria/<int:categoria_id>/templates/', views.get_templates_by_categoria, name='get_templates_by_categoria'),
    path('template/<int:template_id>/atributos/', views.get_atributos_by_template, name='get_atributos_by_template'),
    path('configuracao/<int:configuracao_id>/componentes/', views.get_components_by_configuration, name='get_components_by_configuration'),
]
