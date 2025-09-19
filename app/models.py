from rest_framework import generics
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

# models.py

class Reserva(models.Model):
    area_comun = models.ForeignKey(
        'AreaComun',
        on_delete=models.CASCADE,
        related_name='reservas',
        help_text="Área común que se está reservando."
    )
    # 📝 CAMBIO CLAVE: Relacionar con Residente, no con Usuario
    residente = models.ForeignKey(
        'Residente',
        on_delete=models.CASCADE,
        related_name='reservas',
        null=True,  # 👈 Added null=True
        blank=True, # 👈 Added blank=True
        help_text="Residente que realiza la reserva."
    )
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(
        max_length=50,
        default='pendiente',
        help_text="Ejemplo: 'pendiente', 'confirmada', 'cancelada'."
    )
    pagada = models.BooleanField(
        default=False,
        help_text="Indica si el costo de la reserva ha sido pagado."
    )

    class Meta:
        # Esto evita reservas duplicadas para el mismo residente en la misma hora
        unique_together = ('residente', 'area_comun', 'fecha', 'hora_inicio')

    def __str__(self):
        return (
            f"Reserva de {self.area_comun.nombre} el {self.fecha} "
            f"por {self.residente.usuario.nombre} {self.residente.usuario.apellido_paterno}"
        )

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
    """
    Modelo principal para las tareas de mantenimiento
    """
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    ESTADO_CHOICES = [
        ('creada', 'Creada'),           # Tarea creada pero no asignada
        ('asignada', 'Asignada'),       # Tarea asignada a trabajador(es)
        ('en_progreso', 'En progreso'), # Al menos un trabajador empezó
        ('completada', 'Completada'),   # Tarea totalmente completada
        ('cancelada', 'Cancelada'),     # Tarea cancelada
    ]

    # Información básica de la tarea
    titulo = models.CharField(max_length=200, help_text="Título breve de la tarea",null=True, blank=True,)
    descripcion = models.TextField(help_text="Descripción detallada del trabajo a realizar",null=True, blank=True,)
    

    # Ubicación de la tarea (solo UNA de estas opciones)
    casa = models.ForeignKey(
        'Casa',
        on_delete=models.SET_NULL,
        related_name='tareas_mantenimiento',
        null=True, blank=True,
        help_text="Casa específica donde se realizará el trabajo (opcional)"
    )
    area_comun = models.ForeignKey(
        'AreaComun',
        on_delete=models.SET_NULL,
        related_name='tareas_mantenimiento',
        null=True, blank=True,
        help_text="Área común donde se realizará el trabajo (opcional)"
    )
    ubicacion_personalizada = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descripción de ubicación si no es casa ni área común específica"
    )
    
    # Propiedades de la tarea
    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDAD_CHOICES,
        default='media'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='creada'
    )
    
    # Fechas importantes
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    
    
    # Costos estimados/reales
    costo_estimado = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        help_text="Costo estimado de la tarea"
    )
    

    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = "Tarea de Mantenimiento"
        verbose_name_plural = "Tareas de Mantenimiento"
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
        unique_together = ('usuario', 'casa')

    def __str__(self):
        return f"{self.usuario.nombre} {self.usuario.apellido_paterno} - {self.get_rol_residencia_display()} en {self.casa.numero_casa}"
'''
@receiver(post_delete, sender=Inquilino)
def delete_related_user(sender, instance, **kwargs):
    user = instance.usuario
    if not hasattr(user, 'administrador') and not hasattr(user, 'personal'):
        user.delete()  # ← ¡SE EJECUTA!
 '''

# models.py

class Comunicado(models.Model):
    TITULO_MAX_LENGTH = 200
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('publicado', 'Publicado'),
        ('archivado', 'Archivado'),
    ]

    titulo = models.CharField(max_length=TITULO_MAX_LENGTH)
    contenido = models.TextField(help_text="Contenido del comunicado en formato texto plano o HTML")
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Cuando se hizo visible a los residentes"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador'
    )
    # Opcional: ¿Dirigido a una casa específica? ¿O a todo el condominio?
    casa_destino = models.ForeignKey(
        Casa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='comunicados',
        help_text="Si es nulo, va dirigido a todo el condominio"
    )
    # Opcional: Adjuntar archivo (PDF, imagen, etc.)
    archivo_adjunto = models.FileField(
        upload_to='comunicados_adjuntos/',
        null=True,
        blank=True
    )
    # Opcional: Fecha de expiración del comunicado
    fecha_expiracion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Después de esta fecha, el comunicado ya no se muestra"
    )

    class Meta:
        ordering = ['-fecha_publicacion', '-fecha_creacion']
        verbose_name = "Comunicado"
        verbose_name_plural = "Comunicados"

    def __str__(self):
        return f"{self.titulo} ({self.get_estado_display()}) - {self.fecha_publicacion or 'No publicado'}"
class ConceptoPago(models.Model):
    nombre = models.CharField(max_length=100)  # Ej: "Expensa Mensual", "Multa por ruido", "Alquiler Salón"
    descripcion = models.TextField(blank=True, null=True)
    es_fijo = models.BooleanField(default=False)  # Si el monto es fijo o variable
    monto_fijo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    
class Cuota(models.Model):
    concepto = models.ForeignKey(ConceptoPago, on_delete=models.PROTECT)
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='cuotas')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    periodo = models.DateField()  
    fecha_vencimiento = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=[
            ('pendiente', 'Pendiente'),
            ('pagada', 'Pagada'),
            ('vencida', 'Vencida'),
            ('cancelada', 'Cancelada'),
        ],
        default='pendiente'
    )
    fecha_pago = models.DateTimeField(null=True, blank=True)
    generada_automaticamente = models.BooleanField(default=True)

    class Meta:
        unique_together = ('casa', 'periodo', 'concepto')

    def __str__(self):
        return f"{self.concepto.nombre} - Casa {self.casa.numero_casa} - {self.periodo.strftime('%Y-%m')}"    

    
class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('tarjeta', 'Tarjeta de crédito/débito'),
        ('transferencia', 'Transferencia bancaria'),
        ('efectivo', 'Efectivo'),
        ('qr', 'Pago QR'),
    ]

    cuota = models.ForeignKey(Cuota, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos')
    reserva = models.ForeignKey(Reserva, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos')
    concepto = models.ForeignKey(ConceptoPago, on_delete=models.PROTECT)  # Para saber qué se está pagando
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50, choices=METODO_PAGO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True)  # N° de transacción, comprobante, etc.
    pagado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)  # ¿Quién pagó?
    comprobante = models.FileField(upload_to='comprobantes/', null=True, blank=True)

    def __str__(self):
        return f"Pago de {self.monto} - {self.fecha_pago.strftime('%Y-%m-%d')}"