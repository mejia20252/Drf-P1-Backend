from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.dispatch import receiver
from django.db.models.signals import post_delete

class Rol(models.Model):
    nombre = models.CharField(max_length=50)
    grupo = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='rol')
    def __str__(self): return self.nombre

class Usuario(AbstractUser):
    SEXO_CHOICES = (('M', 'Masculino'), ('F', 'Femenino'))
    nombre = models.CharField(max_length=255)
    apellido_paterno = models.CharField(max_length=255)
    apellido_materno = models.CharField(max_length=255)
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, blank=True, null=True)
    def __str__(self):
        return self.username or f"User {self.id}" 

class Telefono(models.Model):
    numero = models.CharField(max_length=20)
    tipo = models.CharField(max_length=50)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='telefonos')
    def __str__(self): return self.numero




class Casa(models.Model):
    estado_ocupacion_choices = [('ocupada', 'Ocupada'), ('desocupada', 'Desocupada'), ('en_mantenimiento', 'En Mantenimiento'), ('suspendida', 'Suspendida')]
    numero_casa = models.CharField(max_length=10, unique=True)
    tipo_de_unidad = models.CharField(max_length=50, help_text="Ej: apartamento, casa, villa")
    numero = models.IntegerField(help_text="Número de la unidad, si es diferente a numero_casa")
    area = models.DecimalField(max_digits=10, decimal_places=2, help_text="Área en metros cuadrados (m²)")
    piso = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Número de piso (solo para edificios o torres)")
    torre_o_bloque = models.CharField(max_length=50, null=True, blank=True, help_text="Nombre o identificador de torre/bloque (Ej: 'Torre A', 'Bloque 3')")
    tiene_parqueo_asignado = models.BooleanField(default=False, help_text="Indica si esta unidad tiene un parqueo asignado")
    numero_parqueo = models.CharField(max_length=20, null=True, blank=True, help_text="Identificador del parqueo asignado (Ej: 'P-102', 'Estacionamiento 5')")
    estado_ocupacion = models.CharField(max_length=20, choices=estado_ocupacion_choices, default='desocupada', help_text="Estado actual de ocupación de la unidad")
    fecha_ultima_actualizacion = models.DateTimeField(auto_now=True, help_text="Última vez que se modificó la información de esta casa")
    observaciones = models.TextField(null=True, blank=True, help_text="Notas adicionales sobre la unidad (problemas, restricciones, etc.)")
    def __str__(self): return f"{self.torre_o_bloque} - Casa {self.numero_casa}" if self.torre_o_bloque else f"Casa {self.numero_casa}"

class ContratoArrendamiento(models.Model):
    arrendatario = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol__nombre': 'Inquilino'}, related_name='contratos_arrendamiento')
    unidad = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='contratos_arrendamiento_casa')
    propietario = models.ForeignKey(Usuario, on_delete=models.CASCADE, limit_choices_to={'rol__nombre': 'Propietario'}, related_name='contratos_arrendamiento_propietario')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    esta_activo = models.BooleanField(default=True)
    class Meta: verbose_name = "Contrato de Arrendamiento"; verbose_name_plural = "Contratos de Arrendamiento"
    def __str__(self): return f"{self.arrendatario} arrienda {self.unidad} desde {self.fecha_inicio}"

class Bitacora(models.Model):
    login = models.DateTimeField()
    logout = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField(null=True, blank=True, help_text="Dirección IPv4 o IPv6 del dispositivo")
    device = models.CharField(max_length=255, null=True, blank=True, help_text="Ubicación aproximada (p.ej. 'Ciudad, País' o 'lat,lon')")
    class Meta: db_table = 'bitacora'

class DetalleBitacora(models.Model):
    bitacora = models.ForeignKey(Bitacora, on_delete=models.CASCADE, related_name='detallebitacoras')
    accion = models.CharField(max_length=100)
    fecha = models.DateTimeField()
    tabla = models.CharField(max_length=50)
    class Meta: db_table = 'detallebitacora'

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


class Mascota(models.Model):
    ESPECIE_CHOICES = [('perro', 'Perro'), ('gato', 'Gato'), ('ave', 'Ave'), ('otro', 'Otro')]
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=50, choices=ESPECIE_CHOICES)
    raza = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    dueno = models.ForeignKey('Residente', on_delete=models.CASCADE, related_name='mascotas')
    foto = models.ImageField(upload_to='mascotas/', blank=True, null=True)
    def __str__(self): return f"{self.nombre} ({self.especie}) de {self.dueno.usuario.nombre}"

class AreaComun(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    costo_alquiler = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    capacidad = models.IntegerField(help_text="Capacidad máxima de personas.")
    estado = models.CharField(max_length=50, default='disponible')
    def __str__(self): return self.nombre

class Reserva(models.Model):
    estado_choices = [('pendiente', 'Pendiente'), ('confirmada', 'Confirmada'), ('cancelada', 'Cancelada')]
    area_comun = models.ForeignKey('AreaComun', on_delete=models.CASCADE, related_name='reservas', help_text="Área común que se está reservando.")
    residente = models.ForeignKey('Residente', on_delete=models.CASCADE, related_name='reservas', null=True, blank=True, help_text="Residente que realiza la reserva.")
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    estado = models.CharField(max_length=50, default='pendiente', choices=estado_choices, help_text="Ejemplo: 'pendiente', 'confirmada', 'cancelada'.")
    class Meta: unique_together = ('residente', 'area_comun', 'fecha', 'hora_inicio')
    def __str__(self): return f"Reserva de {self.area_comun.nombre} el {self.fecha} por {self.residente.usuario.nombre} {self.residente.usuario.apellido_paterno}"



class TareaMantenimiento(models.Model):
    PRIORIDAD_CHOICES = [('baja', 'Baja'), ('media', 'Media'), ('alta', 'Alta'), ('critica', 'Crítica')]
    ESTADO_CHOICES = [('creada', 'Creada'), ('asignada', 'Asignada'), ('en_progreso', 'En progreso'), ('completada', 'Completada'), ('cancelada', 'Cancelada')]
    titulo = models.CharField(max_length=200, help_text="Título breve de la tarea",null=True, blank=True,)
    descripcion = models.TextField(help_text="Descripción detallada del trabajo a realizar",null=True, blank=True,)
    casa = models.ForeignKey('Casa', on_delete=models.SET_NULL, related_name='tareas_mantenimiento', null=True, blank=True, help_text="Casa específica donde se realizará el trabajo (opcional)")
    area_comun = models.ForeignKey('AreaComun', on_delete=models.SET_NULL, related_name='tareas_mantenimiento', null=True, blank=True, help_text="Área común donde se realizará el trabajo (opcional)")
    ubicacion_personalizada = models.CharField(max_length=200, blank=True,null=True, help_text="Descripción de ubicación si no es casa ni área común específica")
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='creada')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Costo estimado de la tarea")
    class Meta: ordering = ['-fecha_creacion']; verbose_name = "Tarea de Mantenimiento"; verbose_name_plural = "Tareas de Mantenimiento"
    def __str__(self): return self.titulo

class Vehiculo(models.Model):
    placa = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=50)
    dueno = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='vehiculos')
    casa = models.ForeignKey('Casa', on_delete=models.SET_NULL, related_name='vehiculos_residentes', null=True, blank=True)
    def __str__(self): return self.placa

class Comunicado(models.Model):
    ESTADO_CHOICES = [('borrador', 'Borrador'), ('publicado', 'Publicado'), ('archivado', 'Archivado')]
    titulo = models.CharField(max_length=200)
    contenido = models.TextField(help_text="Contenido del comunicado en formato texto plano o HTML")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_publicacion = models.DateTimeField(null=True, blank=True, help_text="Cuando se hizo visible a los residentes")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    casa_destino = models.ForeignKey(Casa, on_delete=models.SET_NULL, null=True, blank=True, related_name='comunicados', help_text="Si es nulo, va dirigido a todo el condominio")
    archivo_adjunto = models.FileField(upload_to='comunicados_adjuntos/', null=True, blank=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True, help_text="Después de esta fecha, el comunicado ya no se muestra")
    class Meta: ordering = ['-fecha_publicacion', '-fecha_creacion']; verbose_name = "Comunicado"; verbose_name_plural = "Comunicados"
    def __str__(self): return f"{self.titulo} ({self.get_estado_display()}) - {self.fecha_publicacion or 'No publicado'}"

class ConceptoPago(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    es_fijo = models.BooleanField(default=False)
    monto_fijo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    activo = models.BooleanField(default=True)
    def __str__(self): return self.nombre

class Cuota(models.Model):
    estado_choices = [('pendiente', 'Pendiente'), ('pagada', 'Pagada'), ('vencida', 'Vencida'), ('cancelada', 'Cancelada')]
    concepto = models.ForeignKey(ConceptoPago, on_delete=models.PROTECT)
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='cuotas')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    periodo = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=estado_choices, default='pendiente')
    generada_automaticamente = models.BooleanField(default=True)
    class Meta: unique_together = ('casa', 'periodo', 'concepto')
    def __str__(self): return f"{self.concepto.nombre} - Casa {self.casa.numero_casa} - {self.periodo.strftime('%Y-%m')}"
class Propiedad(models.Model):
    casa = models.OneToOneField(
        Casa,
        on_delete=models.CASCADE,
        related_name='propiedad',
        help_text="Casa a la que pertenece esta propiedad"
    )
    propietario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        limit_choices_to={'rol__nombre': 'Propietario'},
        related_name='propiedades',
        help_text="Usuario propietario de la casa"
    )
    fecha_adquisicion = models.DateField(
        auto_now_add=True,
        help_text="Fecha en que el propietario adquirió la propiedad"
    )
    fecha_transferencia = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que la propiedad fue transferida a otro propietario (si aplica)"
    )
    activa = models.BooleanField(
        default=True,
        help_text="Indica si esta es la asignación de propiedad actual"
    )

    class Meta:
        verbose_name = "Propiedad"
        verbose_name_plural = "Propiedades"
        # Si quieres permitir historial de propietarios, elimina el OneToOneField y usa ForeignKey + unique_together
        # unique_together = ('casa', 'activa')  # Solo una propiedad activa por casa

    def __str__(self):
        return f"{self.propietario.email} es propietario de {self.casa}"
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Pago(models.Model):
    TIPO_PAGO_CHOICES = [
        ('cuota', 'Cuota'),
        ('reserva', 'Reserva de Área Común'),
        ('multa', 'Multa'),
        ('gasto_comun', 'Gasto Común'),
        ('otro', 'Otro'),
    ]

    METODO_PAGO_CHOICES = [
        ('tarjeta', 'Tarjeta de crédito/débito'),
        ('transferencia', 'Transferencia bancaria'),
        ('efectivo', 'Efectivo'),
        ('qr', 'Pago QR'),
    ]

    # Relación directa con el usuario que realizó el pago
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos',
        help_text="Usuario que realizó el pago"
    )

    # Tipo de pago para filtrado rápido
    tipo_pago = models.CharField(max_length=20, choices=TIPO_PAGO_CHOICES,default='cuota')

    # Monto y detalles del pago
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50, choices=METODO_PAGO_CHOICES)
    referencia = models.CharField(max_length=100, blank=True, null=True, help_text="N° de transacción, comprobante, etc.")
    comprobante = models.FileField(upload_to='comprobantes/', null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')


    def __str__(self):
        return f"{self.get_tipo_pago_display()} - {self.monto} - {self.fecha_pago.strftime('%Y-%m-%d')}"

    class Meta:
        ordering = ['-fecha_pago']
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
class PerfilTrabajador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='perfil_trabajador')
    especialidades = models.JSONField(default=list)
    activo = models.BooleanField(default=True)
    
    # 👇 Nuevos campos útiles
    fecha_contratacion = models.DateField(auto_now_add=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    horario_laboral = models.CharField(max_length=200, blank=True, help_text="Ej: 'Lunes a Viernes, 8am-5pm'")
    supervisor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'rol__nombre': 'Administrador'},
        related_name='trabajadores_a_cargo'
    )
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.nombre} ({'Activo' if self.activo else 'Inactivo'})"
from django.utils import timezone

class AsignacionTarea(models.Model):
    tarea = models.ForeignKey(
        TareaMantenimiento,
        on_delete=models.CASCADE,
        related_name='asignaciones',
        help_text="Tarea que se está asignando"
    )
    trabajador = models.ForeignKey(
        PerfilTrabajador,
        on_delete=models.CASCADE,
        related_name='tareas_asignadas',
        help_text="Perfil del trabajador al que se asigna la tarea"
    )
    asignado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tareas_asignadas_por_mi',
        help_text="Usuario que realizó la asignación (ej: administrador)"
    )
    fecha_asignacion = models.DateTimeField(default=timezone.now)
    fecha_completado = models.DateTimeField(null=True, blank=True, help_text="Cuando el trabajador marcó la tarea como completada")
    estado_asignacion = models.CharField(
        max_length=20,
        choices=[
            ('activa', 'Activa'),
            ('completada', 'Completada'),
            ('cancelada', 'Cancelada'),
            ('reasignada', 'Reasignada'),
        ],
        default='activa'
    )
    observaciones = models.TextField(blank=True, null=True, help_text="Notas adicionales sobre esta asignación")

    class Meta:
        verbose_name = "Asignación de Tarea"
        verbose_name_plural = "Asignaciones de Tareas"
        ordering = ['-fecha_asignacion']
        # Evita asignar el mismo trabajador dos veces a la misma tarea
        unique_together = ('tarea', 'trabajador', 'estado_asignacion')

    def __str__(self):
        return f"{self.trabajador.usuario.nombre} asignado a '{self.tarea.titulo or 'Sin título'}'"

    def save(self, *args, **kwargs):
        # Si es una nueva asignación activa, actualiza el estado de la tarea a 'asignada'
        if self.estado_asignacion == 'activa' and not self.pk:
            self.tarea.estado = 'asignada'
            self.tarea.save()

        # Si se marca como completada, actualiza la tarea si es la única asignación activa
        if self.estado_asignacion == 'completada' and not self.fecha_completado:
            self.fecha_completado = timezone.now()
            # Verificar si todas las asignaciones de esta tarea están completadas
            todas_completadas = not self.tarea.asignaciones.filter(estado_asignacion='activa').exists()
            if todas_completadas:
                self.tarea.estado = 'completada'
                self.tarea.save()

        super().save(*args, **kwargs)




#push notification
class DispositivoMovil(models.Model):
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='dispositivos',
        help_text="Usuario propietario del dispositivo"
    )
    token_fcm = models.TextField(
        unique=True,
        help_text="Token de Firebase Cloud Messaging para enviar notificaciones push"
    )
    modelo_dispositivo = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Ej: iPhone 14, Samsung Galaxy S23"
    )
    sistema_operativo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="iOS, Android, etc."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el dispositivo sigue recibiendo notificaciones"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_conexion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Última vez que la app se conectó o renovó el token"
    )

    class Meta:
        verbose_name = "Dispositivo Móvil"
        verbose_name_plural = "Dispositivos Móviles"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.usuario.username} - {self.modelo_dispositivo or 'Dispositivo'}"
class NotificacionPush(models.Model):
    TIPO_NOTIFICACION_CHOICES = [
        ('seguridad', 'Seguridad'),
        ('finanzas', 'Finanzas'),
        ('areas_comunes', 'Áreas Comunes'),
        ('mantenimiento', 'Mantenimiento'),
        ('comunicado', 'Comunicado'),
        ('sistema', 'Sistema'),
    ]

    ESTADO_CHOICES = [
        ('enviada', 'Enviada'),
        ('entregada', 'Entregada'),
        ('leida', 'Leída'),
        ('fallida', 'Fallida'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones_push',
        help_text="Usuario destinatario de la notificación"
    )
    dispositivo = models.ForeignKey(
        DispositivoMovil,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notificaciones_enviadas',
        help_text="Dispositivo al que se envió la notificación"
    )
    titulo = models.CharField(max_length=150)
    cuerpo = models.TextField()
    tipo = models.CharField(max_length=50, choices=TIPO_NOTIFICACION_CHOICES, default='sistema')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='enviada')
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True, help_text="Cuando FCM confirma entrega")
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    datos_adicionales = models.JSONField(
        null=True,
        blank=True,
        help_text="Payload adicional (ej: id de incidente, url, acción)"
    )
    intento_envio = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Notificación Push"
        verbose_name_plural = "Notificaciones Push"
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.titulo} → {self.usuario.username}"
class IncidenteSeguridadIA(models.Model):
    TIPO_INCIDENTE_CHOICES = [
        ('acceso_no_autorizado', 'Acceso No Autorizado'),
        ('persona_desconocida', 'Persona Desconocida en Área Restringida'),
        ('vehiculo_mal_estacionado', 'Vehículo Mal Estacionado'),
        ('perro_suelto', 'Perro Suelto'),
        ('perro_haciendo_necesidades', 'Perro Haciendo Necesidades'),
    ]

    tipo = models.CharField(max_length=50, choices=TIPO_INCIDENTE_CHOICES)
    descripcion = models.TextField()
    fecha_hora = models.DateTimeField(auto_now_add=True)
    ubicacion = models.CharField(max_length=255, help_text="Ej: Entrada principal, Torre A, Piscina")
    imagen_evidencia = models.ImageField(upload_to='incidentes/', null=True, blank=True)
    notificacion_enviada = models.ForeignKey(
        NotificacionPush,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidentes_asociados'
    )
    resuelto = models.BooleanField(default=False)
    resuelto_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incidentes_resueltos'
    )
    fecha_resolucion = models.DateTimeField(null=True, blank=True)