from django.db import models 
from rest_framework import serializers
#login
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import (
    Rol, Usuario, Telefono,  Casa, ContratoArrendamiento,
    Bitacora, DetalleBitacora, Residente, Mascota, AreaComun, Reserva,
     TareaMantenimiento, Vehiculo, Comunicado, ConceptoPago,
    Cuota, Propiedad,Pago
)
from django.contrib.auth.models import Group, Permission as AuthPermission
class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre']
    def create(self, validated_data):
        print("--- Inicio del método create() en RolSerializer ---")
        
        # 1. Extrae el nombre del rol
        rol_name = validated_data.get('nombre')
        print(f"1. Nombre de rol extraído: {rol_name}")

        try:
            # 2. Busca si ya existe un grupo con ese nombre
            group = Group.objects.get(name=rol_name)
            print(f"2. Grupo existente encontrado: {group.name}")
        except Group.DoesNotExist:
            print(f"2. ¡Advertencia! No se encontró un grupo llamado '{rol_name}'.")
            # Podrías crear el grupo si no existe, o manejar el error
            raise serializers.ValidationError(f"No existe un grupo con el nombre '{rol_name}'.")

        # 3. Asigna el grupo existente al nuevo rol
        print(f"3. Intentando crear el Rol con el grupo ID: {group.id}")
        rol = Rol.objects.create(grupo=group, **validated_data)
        
        print("--- Rol creado exitosamente ---")
        return rol
#Cuando pones rol = RolSerializer(read_only=True), le estás diciendo a DRF:
#“Este campo solo se usa para lectura. Ignora cualquier valor que venga en el payload de escritura (POST/PUT/PATCH).” 
class UsuarioSerializer(serializers.ModelSerializer):
    rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(),
        required=True
    )

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'nombre', 'apellido_paterno', 'apellido_materno',
            'sexo', 'direccion', 'fecha_nacimiento', 'rol', 'password'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Usuario(**validated_data)
        if password:
            user.set_password(password)  # ✅ ESTO HASHEA LA CONTRASEÑA
        user.save()
        return user

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['rol_nombre'] = instance.rol.nombre if instance.rol else None
        return rep

class TelefonoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Telefono
        fields = '__all__'



class CasaSerializer(serializers.ModelSerializer):
    propietario_actual = serializers.SerializerMethodField()
    tiene_propietario_activo = serializers.SerializerMethodField()

    class Meta:
        model = Casa
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['propietario_actual'] = self.get_propietario_actual(instance)
        data['tiene_propietario_activo'] = self.get_tiene_propietario_activo(instance)
        return data

    # ... tus métodos get_... siguen igual
    # ... tus métodos get_... siguen igual
    def get_propietario_actual(self, obj):
        # Accede a la propiedad activa precargada
        prop = getattr(obj, '_prefetched_objects_cache', {}).get('propiedades', [])
        if prop:
            prop = prop[0]  # Ya filtramos solo activas en el Prefetch
            return {
                'id': prop.propietario.id,
                'nombre': f"{prop.propietario.nombre} {prop.propietario.apellido_paterno}",
                'email': prop.propietario.email,
                'rol': prop.propietario.rol.nombre if prop.propietario.rol else None
            }
        return None

    def get_tiene_propietario_activo(self, obj):
        prop = getattr(obj, '_prefetched_objects_cache', {}).get('propiedades', [])
        return len(prop) > 0

class ContratoArrendamientoSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información relevante de las FK
    arrendatario_nombre_completo = serializers.SerializerMethodField()
    arrendatario_email = serializers.EmailField(source='arrendatario.email', read_only=True)
    unidad_numero_casa = serializers.CharField(source='unidad.numero_casa', read_only=True)
    unidad_tipo = serializers.CharField(source='unidad.tipo_de_unidad', read_only=True)
    propietario_nombre_completo = serializers.SerializerMethodField()
    propietario_email = serializers.EmailField(source='propietario.email', read_only=True)

    class Meta:
        model = ContratoArrendamiento
        fields = [
            'id', 'arrendatario', 'arrendatario_nombre_completo', 'arrendatario_email',
            'unidad', 'unidad_numero_casa', 'unidad_tipo',
            'propietario', 'propietario_nombre_completo', 'propietario_email',
            'fecha_inicio', 'fecha_fin', 'esta_activo'
        ]

    def get_arrendatario_nombre_completo(self, obj):
        if obj.arrendatario:
            return f"{obj.arrendatario.nombre} {obj.arrendatario.apellido_paterno}".strip()
        return None

    def get_propietario_nombre_completo(self, obj):
        if obj.propietario:
            return f"{obj.propietario.nombre} {obj.propietario.apellido_paterno}".strip()
        return None

    def to_representation(self, instance):
        # Obtiene la representación por defecto con los SerializerMethodField y Source
        representation = super().to_representation(instance)
        
        # Opcional: puedes eliminar los IDs de las FK si solo quieres los nombres,
        # pero es útil mantenerlos si el frontend necesita los IDs para hacer otras llamadas.
        # Si quisieras eliminarlos, descomenta las siguientes líneas:
        # representation.pop('arrendatario', None)
        # representation.pop('unidad', None)
        # representation.pop('propietario', None)

        return representation

class BitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitacora
        fields = '__all__'

class DetalleBitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleBitacora
        fields = '__all__'

class ResidenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Residente
        fields = '__all__'

class MascotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mascota
        fields = '__all__'

class AreaComunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaComun
        fields = '__all__'

class ReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = '__all__'



class TareaMantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TareaMantenimiento
        fields = '__all__'

class VehiculoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehiculo
        fields = ['id', 'placa', 'tipo', 'dueno', 'casa']
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.dueno:
            rep['dueno_nombre_completo'] = f"{instance.dueno.nombre} {instance.dueno.apellido_paterno}"
        else:
            rep['dueno_nombre_completo'] = None
        if instance.casa:
            rep['casa_numero_casa'] = instance.casa.numero_casa
        else:
            rep['casa_numero_casa'] = None
        return rep


class ComunicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunicado
        fields = '__all__'

class ConceptoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptoPago
        fields = '__all__'

class CuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuota
        fields = '__all__'

# serializers.py

from rest_framework import serializers
from .models import Propiedad, Casa, Usuario

class PropiedadSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar info amigable
    casa_numero = serializers.CharField(source='casa.numero_casa', read_only=True)
    casa_descripcion = serializers.CharField(source='casa.__str__', read_only=True)
    propietario_nombre = serializers.SerializerMethodField()
    propietario_email = serializers.EmailField(source='propietario.email', read_only=True)

    class Meta:
        model = Propiedad
        fields = [
            'id',
            'casa',
            'casa_numero',
            'casa_descripcion',
            'propietario',
            'propietario_nombre',
            'propietario_email',
            'fecha_adquisicion',
            'fecha_transferencia',
            'activa',
        ]
        read_only_fields = ['fecha_adquisicion']  # Solo se establece al crear

    def get_propietario_nombre(self, obj):
        return f"{obj.propietario.nombre} {obj.propietario.apellido_paterno}".strip()

    def validate_propietario(self, value):
        """Valida que el usuario seleccionado tenga rol 'Propietario'."""
        if not hasattr(value, 'rol') or value.rol.nombre != 'Propietario':
            raise serializers.ValidationError("El usuario seleccionado debe tener el rol de 'Propietario'.")
        return value

    def validate(self, data):
        casa = data.get('casa')
        activa = data.get('activa', True)  # Por defecto, asumimos True si no se envía
        propietario = data.get('propietario')

        if not casa:
            raise serializers.ValidationError({"casa": "La casa es requerida."})

        if not propietario:
            raise serializers.ValidationError({"propietario": "El propietario es requerido."})

        # Si se está creando o activando una propiedad
        if activa:
            # Verificar que no exista otra propiedad activa para esta casa
            propiedad_activa_existente = Propiedad.objects.filter(
                casa=casa,
                activa=True
            )

            # Si estamos actualizando, excluir el registro actual
            if self.instance:
                propiedad_activa_existente = propiedad_activa_existente.exclude(pk=self.instance.pk)

            if propiedad_activa_existente.exists():
                prop_existente = propiedad_activa_existente.first()
                raise serializers.ValidationError({
                    'activa': f"La casa ya tiene un propietario activo: {prop_existente.propietario.email}. "
                              f"Primero desactive esa propiedad antes de activar una nueva."
                })

        # Si se está desactivando, asegurarse de que se proporcione fecha_transferencia
        if not activa and not data.get('fecha_transferencia'):
            raise serializers.ValidationError({
                'fecha_transferencia': "Debe proporcionar la fecha de transferencia al desactivar una propiedad."
            })

        return data

    def create(self, validated_data):
        # Si no se envía fecha_transferencia y activa=False, podríamos asignarla automáticamente
        if not validated_data.get('activa', True) and not validated_data.get('fecha_transferencia'):
            from django.utils import timezone
            validated_data['fecha_transferencia'] = timezone.now().date()

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Si se está desactivando y no hay fecha_transferencia, asignarla
        if not validated_data.get('activa', instance.activa) and not validated_data.get('fecha_transferencia'):
            if instance.activa:  # Solo si estaba activa y ahora se desactiva
                from django.utils import timezone
                validated_data['fecha_transferencia'] = timezone.now().date()

        return super().update(instance, validated_data)

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        target_user = self.context["user"]          # usuario al que se le cambia la contraseña
        current = attrs.get("current_password") or ""
        new = attrs["new_password"]
        confirm = attrs["confirm_new_password"]

        if new != confirm:
            raise serializers.ValidationError({"confirm_new_password": "Las contraseñas no coinciden."})

        # si es el/la mism@, debe enviar y validar la contraseña actual
        is_self = request.user.pk == target_user.pk
        is_admin = getattr(request.user, "is_superuser", False)

        if is_self and not current:
            raise serializers.ValidationError({"current_password": "Obligatoria para cambiar tu propia contraseña."})

        if is_self and not target_user.check_password(current):
            raise serializers.ValidationError({"current_password": "No coincide con tu contraseña actual."})

        if target_user.check_password(new):
            raise serializers.ValidationError({"new_password": "La nueva contraseña no puede ser igual a la actual."})

        # si no es self, debe ser admin
        if not is_self and not is_admin:
            raise serializers.ValidationError({"non_field_errors": "No tienes permiso para cambiar esta contraseña."})

        return attrs
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs
    def save(self, **kwargs):
        RefreshToken(self.token).blacklist()
class MyTokenPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):#@
        username=attrs.get(self.username_field) or attrs.get('username')
        password=attrs.get('password')
        User=get_user_model()
        user=User.objects.filter(username=username).first()
        print(user)
        if not user:
            raise AuthenticationFailed('el usuario no existe')
        if not user.check_password(password):
            raise AuthenticationFailed('ingrese su contrase;a correctemetn')
        
            
        return super().validate(attrs)  
class AuthPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthPermission
        fields = ['id', 'codename', 'name'] 
              
class GroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=AuthPermission.objects.all(),
        many=True
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']
class UsuarioMeSerializer(serializers.ModelSerializer):
    """
    Serializador exclusivo para el endpoint '/usuarios/me/'.
    """
    rol = RolSerializer(read_only=True) # Utiliza el RolSerializer para serializar el objeto completo

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "nombre",
            "apellido_paterno",
            "apellido_materno",
            "sexo",
            "email",
            "fecha_nacimiento",
            "rol",
        ]
class PagoSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información relacionada
    usuario_nombre = serializers.SerializerMethodField()
    tipo_pago_display = serializers.CharField(source='get_tipo_pago_display', read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    
    # Campos para el objeto genérico relacionado
    objeto_relacionado_tipo = serializers.SerializerMethodField()
    objeto_relacionado_id = serializers.SerializerMethodField()
    objeto_relacionado_descripcion = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            'id', 'usuario', 'usuario_nombre', 'tipo_pago', 'tipo_pago_display',
            'monto', 'fecha_pago', 'metodo_pago', 'metodo_pago_display',
            'referencia', 'comprobante', 'observaciones',
            'objeto_relacionado_tipo', 'objeto_relacionado_id', 'objeto_relacionado_descripcion'
        ]
        read_only_fields = ['fecha_pago', 'comprobante'] # El comprobante se genera por la señal

    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.nombre} {obj.usuario.apellido_paterno}".strip()
        return None
    
    def get_objeto_relacionado_tipo(self, obj):
        if obj.content_object:
            return obj.content_object._meta.verbose_name
        return None

    def get_objeto_relacionado_id(self, obj):
        if obj.content_object:
            return obj.content_object.id
        return None
        
    def get_objeto_relacionado_descripcion(self, obj):
        if obj.content_object:
            # Aquí puedes personalizar cómo quieres describir cada tipo de objeto.
            # Por ejemplo, para una Cuota podrías mostrar el concepto y la casa.
            # Para una Reserva, el área común y la fecha.
            if isinstance(obj.content_object, Cuota):
                return f"{obj.content_object.concepto.nombre} - Casa {obj.content_object.casa.numero_casa} ({obj.content_object.get_estado_display()})"
            elif isinstance(obj.content_object, Reserva):
                return f"Reserva de {obj.content_object.area_comun.nombre} el {obj.content_object.fecha} ({obj.content_object.get_estado_display()})"
            # Añade más casos si tienes otros tipos de objetos relacionados
            return str(obj.content_object) # Fallback a la representación por defecto del objeto
        return None

    def create(self, validated_data):
        # Si el tipo de pago es 'cuota' o 'reserva', asegúrate de que el content_object
        # y content_type se asignen correctamente. Esto es importante si el pago no viene de Stripe
        # y quieres crear pagos de forma manual a través de la API.
        tipo_pago = validated_data.get('tipo_pago')
        content_object = validated_data.pop('content_object', None) # Extraer si se pasó en validated_data

        if content_object:
            validated_data['content_type'] = ContentType.objects.get_for_model(content_object)
            validated_data['object_id'] = content_object.id
        elif tipo_pago in ['cuota', 'reserva'] and not (validated_data.get('content_type') and validated_data.get('object_id')):
            # Si es un pago de cuota o reserva, y no se proporcionó el objeto genérico,
            # deberías validar que se asigne correctamente, o lanzar un error.
            # Para este ejemplo, lo dejaremos pasar, asumiendo que el frontend o Stripe lo gestiona.
            # En un caso real de creación manual, necesitarías campos para `cuota_id` o `reserva_id`.
            pass # Aquí puedes añadir lógica de validación más estricta si es necesario

        return super().create(validated_data)

    # Puedes sobrescribir `to_internal_value` si necesitas un manejo especial de
    # cómo se reciben los datos para el content_object durante la creación o actualización.
    # Por ahora, el serializador genérico de Django REST Framework debería manejarlo bien
    # si se envía `content_type` y `object_id` directamente, o si se maneja en `create` como arriba.

class AsignarCasaAVehiculoSerializer(serializers.Serializer):
    """
    Serializer para asignar o desasignar una casa a un vehículo.
    """
    casa = serializers.PrimaryKeyRelatedField(
        queryset=Casa.objects.all(),
        allow_null=True,  # Permite desasignar la casa
        required=False    # Puede ser opcional si el objetivo es solo desasignar
    )

    def validate_casa(self, value):
        # The PrimaryKeyRelatedField already handles fetching the Casa instance
        # if a valid ID is provided, or sets it to None if allow_null is True
        # and the value is null/empty. So this custom validation might be redundant
        # unless you have specific additional checks.
        return value

    def save(self, **kwargs):
        vehiculo = kwargs.get('vehiculo')
        if not vehiculo:
            raise serializers.ValidationError("Se requiere un objeto Vehiculo para esta operación.")

        # self.validated_data.get('casa') will directly give you the Casa instance or None
        # because PrimaryKeyRelatedField handles the conversion.
        new_casa_instance = self.validated_data.get('casa')
        
        vehiculo.casa = new_casa_instance
        vehiculo.save()
        
        return vehiculo
from rest_framework import serializers
from .models import PerfilTrabajador, TareaMantenimiento, AsignacionTarea, Usuario # Importa los modelos necesarios

# --- Serializer para PerfilTrabajador ---
class PerfilTrabajadorSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información amigable del usuario
    usuario_nombre_completo = serializers.SerializerMethodField()
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    # Campos de solo lectura para mostrar información del supervisor
    supervisor_nombre_completo = serializers.SerializerMethodField()
    supervisor_email = serializers.EmailField(source='supervisor.email', read_only=True)

    class Meta:
        model = PerfilTrabajador
        fields = [
            'id', 'usuario', 'usuario_nombre_completo', 'usuario_email', 'usuario_username',
            'especialidades', 'activo', 'fecha_contratacion', 'salario', 'horario_laboral',
            'supervisor', 'supervisor_nombre_completo', 'supervisor_email', 'observaciones'
        ]
        read_only_fields = ['fecha_contratacion'] # La fecha se auto-establece al crear

    def get_usuario_nombre_completo(self, obj):
        if obj.usuario:
            return f"{obj.usuario.nombre} {obj.usuario.apellido_paterno}".strip()
        return None

    def get_supervisor_nombre_completo(self, obj):
        if obj.supervisor:
            return f"{obj.supervisor.nombre} {obj.supervisor.apellido_paterno}".strip()
        return None

    def validate_usuario(self, value):
        """Valida que el usuario seleccionado para el perfil sea único (OneToOneField)"""
        if self.instance and self.instance.usuario == value:
            return value # Si es el mismo usuario en una actualización, no hay problema
        
        # Si se está creando o cambiando el usuario, verifica que no tenga ya un PerfilTrabajador
        if PerfilTrabajador.objects.filter(usuario=value).exists():
            raise serializers.ValidationError("Este usuario ya tiene un perfil de trabajador asignado.")
        return value

    def validate_supervisor(self, value):
        """Valida que el supervisor, si se proporciona, tenga el rol de 'Administrador'."""
        if value and (not hasattr(value, 'rol') or value.rol.nombre != 'Administrador'):
            raise serializers.ValidationError("El supervisor debe tener el rol de 'Administrador'.")
        return value

    def to_representation(self, instance):
        # La representación ya incluye los SerializerMethodField, no necesitas hacer nada extra aquí
        return super().to_representation(instance)


# --- Serializer para AsignacionTarea ---
class AsignacionTareaSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información amigable
    tarea_titulo = serializers.CharField(source='tarea.titulo', read_only=True)
    tarea_estado = serializers.CharField(source='tarea.estado', read_only=True)
    trabajador_nombre_completo = serializers.SerializerMethodField()
    trabajador_email = serializers.EmailField(source='trabajador.usuario.email', read_only=True)
    asignado_por_nombre_completo = serializers.SerializerMethodField()
    asignado_por_email = serializers.EmailField(source='asignado_por.email', read_only=True)
    estado_asignacion_display = serializers.CharField(source='get_estado_asignacion_display', read_only=True)

    class Meta:
        model = AsignacionTarea
        fields = [
            'id', 'tarea', 'tarea_titulo', 'tarea_estado',
            'trabajador', 'trabajador_nombre_completo', 'trabajador_email',
            'asignado_por', 'asignado_por_nombre_completo', 'asignado_por_email',
            'fecha_asignacion', 'fecha_completado', 'estado_asignacion', 'estado_asignacion_display',
            'observaciones'
        ]
        read_only_fields = ['fecha_asignacion', 'fecha_completado']

    def get_trabajador_nombre_completo(self, obj):
        if obj.trabajador and obj.trabajador.usuario:
            return f"{obj.trabajador.usuario.nombre} {obj.trabajador.usuario.apellido_paterno}".strip()
        return None

    def get_asignado_por_nombre_completo(self, obj):
        if obj.asignado_por:
            return f"{obj.asignado_por.nombre} {obj.asignado_por.apellido_paterno}".strip()
        return None

    def validate(self, data):
        # Validación para unique_together ('tarea', 'trabajador', 'estado_asignacion')
        tarea = data.get('tarea')
        trabajador = data.get('trabajador')
        estado_asignacion = data.get('estado_asignacion', 'activa') # Si no se envía, se asume 'activa' por defecto del modelo

        # Si se está creando o actualizando a 'activa'
        if estado_asignacion == 'activa':
            # Contar asignaciones activas existentes para esta tarea y trabajador
            existing_active_assignments = AsignacionTarea.objects.filter(
                tarea=tarea,
                trabajador=trabajador,
                estado_asignacion='activa'
            )

            if self.instance: # Si es una actualización, excluye la instancia actual
                existing_active_assignments = existing_active_assignments.exclude(pk=self.instance.pk)

            if existing_active_assignments.exists():
                raise serializers.ValidationError(
                    f"El trabajador '{trabajador.usuario.nombre}' ya tiene una asignación activa para la tarea '{tarea.titulo}'."
                )

        # Si se completa una tarea, valida que no haya asignaciones activas pendientes
        # Esta lógica está también en el save del modelo, pero puede ser útil replicarla aquí
        # para dar feedback antes de la base de datos.
        if estado_asignacion == 'completada' and self.instance and self.instance.estado_asignacion == 'activa':
            # Se permite que se complete, la lógica del modelo se encargará de actualizar la tarea.
            pass
        
        # Aquí puedes añadir más validaciones si, por ejemplo, solo un administrador
        # puede asignar o cancelar tareas.
        request = self.context.get('request', None)
        if request and request.user and not request.user.is_superuser and request.user.rol and request.user.rol.nombre != 'Administrador':
            # Los no-admins solo pueden cambiar el estado a 'completada' si son el trabajador asignado
            if self.instance and self.instance.trabajador.usuario != request.user:
                raise serializers.ValidationError("Solo el trabajador asignado puede completar esta tarea.")
            
            # Los no-admins no pueden crear nuevas asignaciones (solo los administradores)
            if not self.instance: # Si es una operación de creación
                 raise serializers.ValidationError("Solo los administradores pueden crear nuevas asignaciones de tareas.")

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['asignado_por'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Si se intenta cambiar el trabajador o la tarea, es mejor denegarlo
        # o manejarlo como una reasignación compleja (crear nueva, desactivar anterior)
        if 'tarea' in validated_data and instance.tarea != validated_data['tarea']:
            raise serializers.ValidationError({"tarea": "No se permite cambiar la tarea de una asignación existente. Considere crear una nueva asignación."})
        if 'trabajador' in validated_data and instance.trabajador != validated_data['trabajador']:
            raise serializers.ValidationError({"trabajador": "No se permite cambiar el trabajador de una asignación existente. Considere reasignar (crear nueva)."})

        # Si el estado_asignacion cambia a 'completada' y no se envía fecha_completado, el modelo lo establecerá.
        # Si se está desactivando o cancelando, la lógica del modelo se encarga de no establecer fecha_completado
        return super().update(instance, validated_data)