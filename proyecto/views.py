from django.shortcuts import render, redirect  # Para renderizar plantillas y redirigir
from proyecto.models import User, Tipo  # Importa el modelo de usuario personalizado
from django.contrib import messages  # Para mostrar mensajes de error o éxito
from django.contrib.auth import authenticate, login, logout  # Funciones de autenticación
from django.contrib.auth.decorators import login_required  # Para restringir acceso a vistas protegidas
from django.contrib.auth.hashers import make_password  # Para encriptar contraseñas
from django.contrib.auth import get_user_model  # Para obtener el modelo de usuario personalizado
from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required

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

@login_required(login_url='custom_login')
def home(request):
    return render(request, 'home/index.html', {'usuario': request.user})

def custom_logout(request):
    logout(request)
    response = redirect('custom_login')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

@login_required(login_url='custom_login')
def vista_usuario(request):
    roles = Tipo.objects.exclude(nombre__in=['root'])
    return render(request, 'usuario/index.html', {'usuario': request.user, 'roles': roles})

@login_required(login_url='custom_login')
def crear_usuario(request):
    # Verificamos si la petición es de tipo POST (cuando se envía el formulario)
    if request.method == 'POST':
        # Obtenemos los datos del formulario
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        username = request.POST.get('username')
        password = request.POST.get('password')
        tipo_id = request.POST.get('rol')  # ID del rol seleccionado en el formulario

        # Validaciones básicas antes de crear el usuario

        # Verificar si el nombre de usuario ya existe
        if User.objects.filter(username=username).exists():
            messages.error(request, "El nombre de usuario ya existe.")
            return redirect('vista_usuario')

        # Validar que todos los campos sean ingresados
        if not nombre or not apellido or not username or not password or not tipo_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return redirect('vista_usuario')

        # Intentamos obtener el tipo de usuario (rol) seleccionado
        try:
            tipo = Tipo.objects.get(id=tipo_id)
        except Tipo.DoesNotExist:
            messages.error(request, "El rol seleccionado no es válido.")
            return redirect('vista_usuario')

        # Crear el usuario con la contraseña encriptada para mayor seguridad
        user = User.objects.create(
            first_name=nombre,
            last_name=apellido,
            username=username,
            password=make_password(password),  # Encripta la contraseña antes de guardarla
            tipo=tipo  # Asigna el tipo de usuario seleccionado
        )

        # Mensaje de éxito y redirección después de crear el usuario
        messages.warning(request, "Usuario creado exitosamente.")
        return redirect('vista_usuario')

    # Si la petición es de tipo GET (cuando se carga la página del formulario)
    
    # Obtener todos los usuarios registrados en el sistema
    usuarios = User.objects.all()
    # Obtener todos los roles disponibles
    roles = Tipo.objects.all()

    # Construimos una lista de tuplas con cada usuario y su respectivo rol
    usuarios_con_rol = [(usuario, usuario.tipo.nombre if usuario.tipo else 'Sin rol') for usuario in usuarios]

    # Construimos el contexto que se pasará al template
    context = {
        'username': request.user.username,  # Nombre de usuario autenticado
        'role_name': request.user.tipo.nombre if request.user.tipo else 'Sin rol',  # Rol del usuario autenticado
        'usuarios_con_rol': usuarios_con_rol,  # Lista de usuarios con sus roles
        'roles': roles,  # Lista de roles disponibles
    }

    # Renderizamos la plantilla con el contexto
    return render(request, 'usuario/crear.html', context)
