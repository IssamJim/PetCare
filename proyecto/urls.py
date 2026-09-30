from django.urls import path
from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Tipo

def vista_login(request):
    return render(request, 'Login/index.html')

def custom_login(request):
    request.method = 'POST'


def home(request):
    return render(request, 'home/index.html')

def custom_logout(request):
    request.method = 'POST'

def vista_usuario(request):
    return render(request, 'usuario/index.html')

def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        role_id = request.POST.get('role')

        # Validar que los campos no estén vacíos
        if not username or not password or not email or not role_id:
            return render(request, 'usuario/index.html', {'error': 'Todos los campos son obligatorios.'})

        # Validar que el nombre de usuario no exista
        if User.objects.filter(username=username).exists():
            return render(request, 'usuario/index.html', {'error': 'El nombre de usuario ya existe.'})

        # Crear el nuevo usuario
        user = User.objects.create_user(username=username, password=password, email=email)
        
        # Asignar el rol al usuario
        try:
            role = Tipo.objects.get(id=role_id)
            user.tipo = role
            user.save()
        except Tipo.DoesNotExist:
            return render(request, 'usuario/index.html', {'error': 'El rol seleccionado no es válido.'})

        return render(request, 'usuario/index.html', {'success': 'Usuario creado exitosamente.'})
    else:
        return render(request, 'usuario/index.html')