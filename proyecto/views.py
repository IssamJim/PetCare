from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, get_user_model

User = get_user_model()
# Create your views here.
def vista_login(request):
    return render(request, 'Login/index.html')

def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
            messages.error(request, 'El usuario no existe.')  
        if user:  # Si el usuario existe
            user_authenticated = authenticate(request,                        username=username, password=password)  
            if user_authenticated is not None:
                if user_authenticated.is_active:  
                    login(request, user_authenticated)  
                    return redirect('home')  
                else:
                    messages.error(request, 'Tu cuenta de usuario está inactiva.')  
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')  
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'Login/index.html')


def home(request):
    return render(request, 'home/index.html', {'usuario': request.user})