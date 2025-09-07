from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    Rol,
    Usuario,
    Telefono,
    Administrador,
    Personal,
    Cliente,
    Bitacora,
    DetalleBitacora,
)

# You can register models without a custom class if you don't need special configurations.
# This is a simple, straightforward way to get them into the admin panel.
admin.site.register(Rol)

# For Usuario, we create a custom Admin class to improve its display.
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
admin.site.register(Usuario, UsuarioAdmin)

# For Telefono, we can also customize the display for better readability.
class TelefonoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'usuario')
    list_filter = ('tipo',)
    search_fields = ('numero',)
admin.site.register(Telefono, TelefonoAdmin)

# Register other models with custom Admin classes for a better user experience.
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'numero_licencia', 'empresa', 'activo')
    list_filter = ('activo', 'fecha_certificacion')
    search_fields = ('usuario__email', 'numero_licencia')
admin.site.register(Administrador, AdministradorAdmin)

class PersonalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'salario', 'fecha_ingreso', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('usuario__email',)
admin.site.register(Personal, PersonalAdmin)

class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_cliente', 'fecha_registro', 'activo')
    list_filter = ('activo', 'tipo_cliente')
    search_fields = ('usuario__email',)
admin.site.register(Cliente, ClienteAdmin)

class BitacoraAdmin(admin.ModelAdmin):
    list_display = ('login', 'logout', 'usuario', 'ip', 'device')
    list_filter = ('usuario', 'login')
    search_fields = ('usuario__email', 'ip')
    date_hierarchy = 'login'
admin.site.register(Bitacora, BitacoraAdmin)

class DetalleBitacoraAdmin(admin.ModelAdmin):
    list_display = ('bitacora', 'accion', 'fecha', 'tabla')
    list_filter = ('tabla', 'accion')
    search_fields = ('tabla', 'accion')
admin.site.register(DetalleBitacora, DetalleBitacoraAdmin)