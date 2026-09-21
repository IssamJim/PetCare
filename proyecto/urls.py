from django.urls import path
from django.shortcuts import render

def vista_login(request):
    return render(request, 'Login/index.html')