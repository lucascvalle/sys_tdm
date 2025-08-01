from django.urls import path
from .views import EstoqueHomeView, AjustarEstoqueView

app_name = 'estoque'

urlpatterns = [
    path('', EstoqueHomeView.as_view(), name='home'),
    path('ajustar_estoque/', AjustarEstoqueView.as_view(), name='ajustar_estoque'),
]
