# app/admin.py
from django.contrib import admin
from django.contrib.auth.models import Group
from .models import (
    Rol,
    Usuario,
    Telefono,
    Administrador,
    Personal,
   
    Bitacora,
    DetalleBitacora,
)

# Ya no es necesario registrar Group, Django lo hace por defecto.

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'grupo']
    search_fields = ['nombre']

    def save_model(self, request, obj, form, change):
        # Aseguramos que el objeto Rol es nuevo
        if not change:
            # Creamos o obtenemos un Group con el mismo nombre
            grupo, created = Group.objects.get_or_create(name=obj.nombre)
            # Asignamos el Group al Rol antes de guardar
            obj.grupo = grupo
            
        # Guardamos el objeto Rol
        super().save_model(request, obj, form, change)

# Para Usuario, creamos una clase Admin personalizada para mejorar su visualización.
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'nombre',
        'apellido_paterno',
        'apellido_materno',
        'email',
        'rol',
    )
    search_fields = (
        'username',
        'nombre',
        'apellido_paterno',
        'apellido_materno',
        'email',
    )
    list_filter = ('rol', 'sexo')

# Para Telefono, también personalizamos la visualización para una mejor legibilidad.
@admin.register(Telefono)
class TelefonoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'usuario')
    list_filter = ('tipo',)
    search_fields = ('numero',)

# Registramos otros modelos con clases Admin personalizadas para una mejor experiencia de usuario.
@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'numero_licencia', 'empresa', 'activo')
    list_filter = ('activo', 'fecha_certificacion')
    search_fields = ('usuario__email', 'numero_licencia')

@admin.register(Personal)
class PersonalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'salario', 'fecha_ingreso', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('usuario__email',)


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('login', 'logout', 'usuario', 'ip', 'device')
    list_filter = ('usuario', 'login')
    search_fields = ('usuario__email', 'ip')
    date_hierarchy = 'login'

@admin.register(DetalleBitacora)
class DetalleBitacoraAdmin(admin.ModelAdmin):
    list_display = ('bitacora', 'accion', 'fecha', 'tabla')
    list_filter = ('tabla', 'accion')
    search_fields = ('tabla', 'accion')