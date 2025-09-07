from django.db import models
from django.contrib.auth.models import AbstractUser
# En tu archivo models.py

from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre
class Usuario(AbstractUser):
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Femenino'),
    )
    nombre = models.CharField(max_length=255)
    apellido_paterno = models.CharField(max_length=255)
    apellido_materno = models.CharField(max_length=255)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    password = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)  # Corrected line
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.email

class Telefono(models.Model):
    numero = models.CharField(max_length=20)
    tipo = models.CharField(max_length=50)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='telefonos')

    def __str__(self):
        return self.numero
    
class Administrador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    numero_licencia = models.CharField(max_length=100, unique=True)
    fecha_certificacion = models.DateField()
    empresa = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Admin: {self.usuario.email}"
class Personal(models.Model):
    TIPO_PERSONAL = [
        ('seguridad', 'Seguridad'),
        ('mantenimiento', 'Mantenimiento'),
        ('limpieza', 'Limpieza'),
        ('jardineria', 'Jardinería'),
    ]
    
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    tipo = models.CharField(max_length=50, choices=TIPO_PERSONAL)
    fecha_ingreso = models.DateField()
    salario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Personal {self.tipo}: {self.usuario.email}"
class Cliente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    fecha_registro = models.DateField(auto_now_add=True)
    tipo_cliente = models.CharField(max_length=50)  # 'propietario', 'inquilino'
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Cliente: {self.usuario.email}"
class Bitacora(models.Model):
    login = models.DateTimeField()
    logout = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IPv4 o IPv6 del dispositivo"
    )
    device = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Ubicación aproximada (p.ej. 'Ciudad, País' o 'lat,lon')"
    )

    class Meta:
        db_table = 'bitacora'

class DetalleBitacora(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE, related_name='detallebitacoras')
    accion = models.CharField(max_length=100)
    fecha = models.DateTimeField()
    tabla = models.CharField(max_length=50)

    class Meta:
        db_table = 'detallebitacora'
