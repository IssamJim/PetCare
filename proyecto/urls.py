from django.urls import path
from django.shortcuts import render

def vista_login(request):
    return render(request, 'Login/index.html')

def custom_login(request):
    request.method = 'POST'


def home(request):
    return render(request, 'home/index.html')