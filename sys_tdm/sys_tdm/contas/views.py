from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib import messages

# Create your views here.
def custom_logout_view(request):
    logout(request)
    messages.success(request, "Você foi desconectado com sucesso!")
    return redirect('login') # 'login' é o nome da URL para a página de login