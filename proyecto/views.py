from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login

# Create your views here.
def vista_login(request):
    return render(request, 'Login/index.html')

def custom_login(request):  
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            messages.error(request, 'Usuario no encontrado.')

        if user:
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')  # Redirige a la página de inicio después del inicio de sesión exitoso
                else:
                    messages.error(request, 'La cuenta de usuario está desactivada.')
            else:
                messages.error(request, 'Usuario no existe.')
        else:
            messages.error(request, 'usuario o contraseña incorrectos.')
    return render(request, 'Login/index.html')

def home(request):
    return render(request, 'home/index.html')