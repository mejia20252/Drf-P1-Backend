from django.db import models
from django.contrib.auth.models import AbstractUser,Group
# En tu archivo models.py
from django.dispatch import receiver
from django.db.models.signals import post_delete
from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=50)
    grupo = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='rol')

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
    # Número de licencia profesional del administrador
    numero_licencia = models.CharField(max_length=100, unique=True)
    # Fecha en que el administrador obtuvo su certificación o licencia
    fecha_certificacion = models.DateField( blank=True, null=True)
    # Empresa o compañía para la que trabaja el administrador
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
# En tu archivo models.py


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
# En tu archivo models.py
# En tu archivo models.py

# ... (Modelos anteriores) ...

class Mascota(models.Model):
    ESPECIE_CHOICES = [
        ('perro', 'Perro'),
        ('gato', 'Gato'),
        ('ave', 'Ave'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50, choices=ESPECIE_CHOICES)
    raza = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    
    # La mascota pertenece a un residente (puede ser propietario, inquilino o familiar)
    dueno = models.ForeignKey(
        'Residente',
        on_delete=models.CASCADE,
        related_name='mascotas'
    )
    
    # Campo para subir una foto de la mascota
    foto = models.ImageField(upload_to='mascotas/', blank=True, null=True)

    def __str__(self):
        # Esta línea podría necesitar un ajuste para mostrar el nombre del dueño
        return f"{self.nombre} ({self.especie}) de {self.dueno.usuario.nombre}"

class Propietario(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    # Aquí puedes agregar campos específicos para Propietarios
    # Por ejemplo, una fecha en que adquirió la propiedad.
    fecha_adquisicion = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Propietario de: {self.usuario.email}"


# Modelo Inquilino
# Un Inquilino ocupa una casa que ya tiene un Propietario
class Inquilino(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)

    # Aquí puedes agregar campos específicos para Inquilinos
    # Por ejemplo, la fecha de inicio del contrato de alquiler.
    fecha_inicio_contrato = models.DateField(blank=True, null=True)
    # y la fecha de finalización del contrato.
    fecha_fin_contrato = models.DateField(blank=True, null=True)
    
    def __str__(self):
        return f"Inquilino de: {self.usuario.email}"
class Casa(models.Model):
    numero_casa = models.CharField(max_length=10, unique=True)
    # New fields added below
    tipo_de_unidad = models.CharField(
        max_length=50, 
        help_text="Ej: apartamento, casa, villa"
    )
    numero = models.IntegerField(
        help_text="Número de la unidad, si es diferente a numero_casa"
    )
    area = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Área en metros cuadrados (m²)"
    )
    # Relación con el propietario, el dueño de la casa
    propietario = models.ForeignKey(
        Propietario, 
        on_delete=models.SET_NULL, 
        related_name='casas_propietario', 
        null=True, blank=True
    )
    
    def __str__(self):
        return f"Casa{self.numero_casa}"

class AreaComun(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    costo_alquiler = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00
    )
    capacidad = models.IntegerField(
        help_text="Capacidad máxima de personas."
    )
    # Ejemplo: 'disponible', 'mantenimiento', 'cerrada'
    estado = models.CharField(
        max_length=50, 
        default='disponible'
    )
    
    def __str__(self):
        return self.nombre
# En tu archivo models.py

class Reserva(models.Model):
    area_comun = models.ForeignKey(
        'AreaComun',
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    # Relaciona la reserva con el usuario que la realiza.
    # Usar el modelo 'Usuario' es más flexible, ya que un inquilino,
    # propietario, o incluso un administrador podría hacer una reserva.
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='reservas'
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    # Por ejemplo, 'pendiente', 'confirmada', 'cancelada'
    estado = models.CharField(
        max_length=50,
        default='pendiente'
    )
    # Un campo para indicar si la reserva ha sido pagada.
    pagada = models.BooleanField(default=False)

    def __str__(self):
        return f"Reserva de {self.area_comun.nombre} el {self.fecha} por {self.usuario.nombre}"
# En tu archivo models.py

class PagoReserva(models.Model):
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='pago'
    )
    monto = models.DecimalField(
        max_digits=8,
        decimal_places=2
    )
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50) # Ejemplo: 'Tarjeta', 'Efectivo', 'Transferencia'

    def __str__(self):
        return f"Pago de {self.monto} para la reserva de {self.reserva.usuario.nombre}"    


# En tu archivo models.py

class TareaMantenimiento(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    # El administrador que crea la tarea
    administrador_asigna = models.ForeignKey(
        'Administrador',
        on_delete=models.SET_NULL,
        related_name='tareas_asignadas',
        null=True, blank=True
    )
    # El personal asignado a la tarea
    personal_asignado = models.ForeignKey(
        'Personal',
        on_delete=models.SET_NULL,
        related_name='tareas_recibidas',
        null=True, blank=True
    )
    # Descripción de la tarea
    descripcion = models.TextField()
    # Relaciona la tarea con una casa, si aplica
    casa = models.ForeignKey(
        'Casa',
        on_delete=models.SET_NULL,
        related_name='tareas_mantenimiento',
        null=True, blank=True
    )
    # Opcionalmente, relaciona la tarea con un área común
    area_comun = models.ForeignKey(
        'AreaComun',
        on_delete=models.SET_NULL,
        related_name='tareas_mantenimiento',
        null=True, blank=True
    )
    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDAD_CHOICES,
        default='media'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_limite = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Tarea #{self.id}: {self.descripcion[:30]}..."
class Vehiculo(models.Model):
    placa = models.CharField(max_length=20, unique=True)
    # Por ejemplo, 'automóvil', 'motocicleta'
    tipo = models.CharField(max_length=50)
    # El usuario que es dueño del vehículo
    dueno = models.ForeignKey(
        'Usuario', 
        on_delete=models.CASCADE, 
        related_name='vehiculos'
    )
    # La casa a la que peratenece el vehículo
    casa = models.ForeignKey(
        'Casa', 
        on_delete=models.SET_NULL, # Use SET_NULL to avoid deleting the vehicle if the house is deleted
        related_name='vehiculos_residentes',
        null=True,  # Allows the field to be NULL in the database
        blank=True  # Allows the field to be optional in forms
    )

    def __str__(self):
        return self.placa
    
# En tu archivo models.py

# models.py
class Residente(models.Model):
    # Tipos de roles de residencia para una casa
    ROL_RESIDENCIA_CHOICES = [
        ('propietario', 'Propietario'),
        ('familiar', 'Familiar'),
        ('inquilino', 'Inquilino'),
    ]

    # El usuario que vive en la casa
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='residentes'  # 👈 Ahora es "residentes" (plural) — un usuario puede vivir en varias casas? No, pero es mejor así.
    )

    # La casa donde vive el usuario
    casa = models.ForeignKey(
        Casa,
        on_delete=models.CASCADE,
        related_name='residentes'
    )

    # El rol de la persona en la casa
    rol_residencia = models.CharField(
        max_length=20,
        choices=ROL_RESIDENCIA_CHOICES,
        default='familiar'
    )

    fecha_mudanza = models.DateField(auto_now_add=True)

    class Meta:
        # Evita que un mismo usuario esté registrado dos veces en la misma casa
        constraints = [
            models.UniqueConstraint(
                fields=['usuario', 'casa'],
                name='unique_usuario_casa'
            )
        ]

    def __str__(self):
        return f"{self.usuario.nombre} {self.usuario.apellido_paterno} - {self.get_rol_residencia_display()} en {self.casa.numero_casa}"
'''
@receiver(post_delete, sender=Inquilino)
def delete_related_user(sender, instance, **kwargs):
    user = instance.usuario
    if not hasattr(user, 'administrador') and not hasattr(user, 'personal'):
        user.delete()  # ← ¡SE EJECUTA!
 '''