from django.db import models 
from rest_framework import serializers
from django.contrib.auth.hashers import check_password
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
     TareaMantenimiento, Vehiculo, Comunicado, ConceptoPago,RegistroAccesoVehicular,
    Cuota, Propiedad,Pago
)
from .fcm_service import enviar_notificacion_fcm

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
            'password': {'write_only': True,'required': False}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = Usuario(**validated_data)
        if password:
            user.set_password(password)  # ✅ ESTO HASHEA LA CONTRASEÑA
        user.save()
        return user
    def update(self, instance, validated_data):
        # 1. Handle password separately
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        # 2. Call super().update() for other fields
        # This will update all fields present in validated_data
        updated_instance = super().update(instance, validated_data)
        
        # 3. Save the instance if password was changed
        if password:
            updated_instance.save() # Save only if password was updated, otherwise super().update might have saved.
                                   # More robust: always save at the end if you perform a set_password.
        
        return updated_instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['rol_nombre'] = instance.rol.nombre if instance.rol else None
        return rep

class TelefonoSerializer(serializers.ModelSerializer):
    # Campo para el username del usuario, solo lectura
    usuario_username = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Telefono
        fields = '__all__' # Incluye 'usuario' (el ID) y 'usuario_username'
        read_only_fields = ('usuario_username',) # usuario_username no se usa para escritura

    def get_usuario_username(self, obj):
        """
        Retorna el username del usuario asociado.
        """
        return obj.usuario.username if obj.usuario else None


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
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs
    def save(self, **kwargs):
        RefreshToken(self.token).blacklist()
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
class AuthPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthPermission
        fields = ['id', 'codename', 'name']
class ChangePasswordSerializer(serializers.Serializer):
    # current_password será requerido condicionalmente, no por defecto
    current_password = serializers.CharField(required=False, write_only=True)
    new_password = serializers.CharField(min_length=6, write_only=True)
    confirm_new_password = serializers.CharField(min_length=6, write_only=True)

    def validate(self, data):
        request = self.context.get("request")
        target_user = self.context.get("user") # Este es el usuario CUYA contraseña se va a cambiar

        # Verificación de que new_password y confirm_new_password coinciden
        if data["new_password"] != data["confirm_new_password"]:
            raise serializers.ValidationError({"confirm_new_password": "Las nuevas contraseñas no coinciden."})

        # Si el usuario que hace la solicitud es un administrador (o superuser)
        # y no está cambiando su propia contraseña, O si es un superuser
        # podemos omitir la verificación de current_password.
        # Asumimos que un rol de ID 1 es "Administrador". Ajusta esto si tu ID de rol es diferente.
        is_request_user_admin = (request and request.user.is_authenticated and
                                 (request.user.is_superuser or (hasattr(request.user, 'rol') and request.user.rol and request.user.rol.nombre == 'Administrador')))
        
        # Lógica para cambiar la contraseña de otro usuario (solo para administradores)
        if target_user != request.user: # Si el usuario objetivo NO es el usuario autenticado
            if not is_request_user_admin:
                # Un usuario común no puede cambiar la contraseña de otro
                raise serializers.ValidationError({"detail": "No tienes permiso para cambiar la contraseña de otro usuario."})
            
            # Si es un administrador cambiando la contraseña de otro, no necesita current_password del target_user
            # Tampoco necesitamos la current_password del administrador que hace la solicitud aquí.
            data.pop('current_password', None) # Asegurarse de que no esté en los validated_data si se envió por error
        
        # Lógica para cambiar la propia contraseña (requiere current_password)
        else: # target_user == request.user (el usuario está cambiando su propia contraseña)
            current_password = data.get("current_password")
            
            # Si el usuario es administrador y está cambiando su propia contraseña,
            # no le requerimos current_password. (Esto es una elección, se podría requerir por seguridad)
            # Aquí, por la consigna, no lo requerimos si es admin.
            if is_request_user_admin and target_user == request.user:
                 data.pop('current_password', None) # Quitarlo si se envió, no es necesario
            elif not current_password:
                raise serializers.ValidationError({"current_password": "Obligatoria para cambiar tu propia contraseña."})
            elif not check_password(current_password, target_user.password): # Usar check_password para comparar
                raise serializers.ValidationError({"current_password": "Contraseña actual incorrecta."})
            
            if data["new_password"] == current_password:
                raise serializers.ValidationError({"new_password": "La nueva contraseña no puede ser igual a la actual."})

        return data
    


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
    
    def to_representation(self, instance):
        """
        Convert `Decimal` values to string when serializing for API.
        This is useful to match frontend's expectation of string for costo_alquiler.
        """
        representation = super().to_representation(instance)
        if representation.get('costo_alquiler') is not None:
            representation['costo_alquiler'] = str(representation['costo_alquiler'])
        return representation

    def to_internal_value(self, data):
        """
        Convert `costo_alquiler` back to Decimal for the model if it's provided as a string.
        Also handle setting costo_alquiler to 0 if es_de_pago is false.
        """
        # Call the parent's to_internal_value to get initial validated data
        internal_value = super().to_internal_value(data)

        # Handle costo_alquiler based on es_de_pago
        es_de_pago = data.get('es_de_pago', False) # Get from request data first, default to False
        
        if not es_de_pago:
            internal_value['costo_alquiler'] = 0.00 # Set to 0 if not de pago
        elif 'costo_alquiler' in data and data['costo_alquiler'] == '0.00':
             # If it is de pago but costo is "0.00", it means invalid input,
             # Django's DecimalField will handle validation errors if 0.00 is not allowed.
             pass # Let Django's validation handle if 0.00 is valid or not when es_de_pago is True

        return internal_value

from rest_framework import serializers
from .models import Reserva, Residente

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
    # Campo para controlar si se envía notificación, no es parte del modelo
    send_notification = serializers.BooleanField(write_only=True, required=False, default=False)
    # Campo para especificar el grupo de destinatarios (opcional)
    # Puede ser 'todos', 'propietarios', 'inquilinos', 'administradores', 'trabajadores', 'seguridad' o un ID de usuario
    target_recipients = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Campo de solo lectura para el nombre de la casa de destino (si existe)
    casa_destino_nombre = serializers.CharField(source='casa_destino.nombre', read_only=True)

    class Meta:
        model = Comunicado
        fields = [
            'id', 'titulo', 'contenido', 'fecha_creacion', 'fecha_publicacion',
            'estado', 'casa_destino', 'casa_destino_nombre', 'archivo_adjunto', 'fecha_expiracion',
            'send_notification', 'target_recipients' # Campos adicionales para el envío de notificaciones
        ]
        read_only_fields = ['fecha_creacion']

    def create(self, validated_data):
        send_notification = validated_data.pop('send_notification', False)
        target_recipients = validated_data.pop('target_recipients', '')

        comunicado = super().create(validated_data) # Primero crea el comunicado

        if send_notification and comunicado.estado == 'publicado':
            # Solo enviar notificaciones si el comunicado está publicado
            self._send_comunicado_notifications(comunicado, target_recipients)
        
        return comunicado

    def update(self, instance, validated_data):
        send_notification = validated_data.pop('send_notification', False)
        target_recipients = validated_data.pop('target_recipients', '')

        # Captura el estado antiguo para comparar
        old_estado = instance.estado 
        
        comunicado = super().update(instance, validated_data) # Luego actualiza el comunicado

        # Solo enviar notificaciones si:
        # 1. Se solicitó enviar notificación (`send_notification`).
        # 2. El comunicado está 'publicado' Y O BIEN no estaba publicado antes (es una nueva publicación)
        #    O BIEN fue una actualización de un comunicado ya publicado y se requirió la notificación.
        if send_notification and comunicado.estado == 'publicado' and \
           (old_estado != 'publicado' or (old_estado == 'publicado' and send_notification)): # La última condición 'send_notification' es redundante pero clara.
            self._send_comunicado_notifications(comunicado, target_recipients)

        return comunicado

    def _send_comunicado_notifications(self, comunicado, target_recipients):

        titulo_notif = f"Nuevo Comunicado: {comunicado.titulo}"
        cuerpo_notif = comunicado.contenido[:150] + "..." if len(comunicado.contenido) > 150 else comunicado.contenido
        datos_adicionales = {'comunicado_id': str(comunicado.id), 'action': 'OPEN_COMUNICADO'}

        users_to_notify = []

        if target_recipients == 'todos':
            users_to_notify = Usuario.objects.filter(is_active=True)
        elif target_recipients == 'propietarios':
            rol_propietario = Rol.objects.filter(nombre='Propietario').first()
            if rol_propietario:
                users_to_notify = Usuario.objects.filter(rol=rol_propietario, is_active=True)
        elif target_recipients == 'inquilinos':
            rol_inquilino = Rol.objects.filter(nombre='Inquilino').first()
            if rol_inquilino:
                users_to_notify = Usuario.objects.filter(rol=rol_inquilino, is_active=True)
        elif target_recipients == 'administradores':
            rol_admin = Rol.objects.filter(nombre='Administrador').first()
            if rol_admin:
                users_to_notify = Usuario.objects.filter(rol=rol_admin, is_active=True)
        elif target_recipients == 'trabajadores':
            rol_trabajador = Rol.objects.filter(nombre='Trabajador').first()
            if rol_trabajador:
                users_to_notify = Usuario.objects.filter(rol=rol_trabajador, is_active=True)
        elif target_recipients == 'seguridad': # <--- NUEVA LÓGICA PARA ROL SEGURIDAD
            rol_seguridad = Rol.objects.filter(nombre='Seguridad').first()
            if rol_seguridad:
                users_to_notify = Usuario.objects.filter(rol=rol_seguridad, is_active=True)
        elif target_recipients.isdigit(): # Es un ID de usuario específico
            try:
                user_id = int(target_recipients)
                user = Usuario.objects.filter(id=user_id, is_active=True).first()
                if user:
                    users_to_notify = [user]
            except ValueError:
                pass # No es un ID válido, continuar sin agregar.
        else: # Si no se especificó un target_recipients válido, usar la lógica de `casa_destino`
            if comunicado.casa_destino:
                # Notificar a propietarios y residentes de la casa específica
                propietarios_casa = Usuario.objects.filter(
                    propiedades__casa=comunicado.casa_destino,
                    propiedades__activa=True,
                    is_active=True
                ).distinct()
                residentes_casa = Usuario.objects.filter(
                    residentes__casa=comunicado.casa_destino,
                    is_active=True
                ).distinct()
                # Unir ambos querysets
                users_to_notify = (propietarios_casa | residentes_casa).distinct()
            else:
                # Comunicado general (a todo el condominio)
                # Notificar a todos los propietarios y residentes en cualquier casa
                propietarios_condominio = Usuario.objects.filter(
                    propiedades__isnull=False,
                    propiedades__activa=True,
                    is_active=True
                ).distinct()
                residentes_condominio = Usuario.objects.filter(
                    residentes__isnull=False,
                    is_active=True
                ).distinct()
                users_to_notify = (propietarios_condominio | residentes_condominio).distinct()
        
        # Enviar la notificación a cada usuario en la lista
        for user in users_to_notify:
            enviar_notificacion_fcm(
                usuario=user,
                titulo=titulo_notif,
                cuerpo=cuerpo_notif,
                tipo='comunicado',
                datos_adicionales=datos_adicionales
            )
        print(f"Notificaciones de comunicado '{comunicado.titulo}' enviadas a {len(users_to_notify)} usuarios.")
class ConceptoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptoPago
        fields = '__all__'

class CuotaSerializer(serializers.ModelSerializer):
    concepto_nombre = serializers.CharField(source='concepto.nombre', read_only=True)
    casa_numero_casa = serializers.CharField(source='casa.numero_casa', read_only=True)

    class Meta:
        model = Cuota
        fields = '__all__'
        # O si quieres ser explícito, puedes listar todos los campos:
        # fields = ['id', 'concepto', 'casa', 'monto', 'periodo', 'fecha_vencimiento', 
        #           'estado', 'generada_automaticamente', 'concepto_nombre', 'casa_numero_casa']

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



 #


# En serializers.py

# ... tus otros serializadores (RolSerializer, UsuarioSerializer, etc.)

class CustomUserForBitacoraSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True) # Para obtener el nombre del rol

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'nombre', 'apellido_paterno', 'apellido_materno', 'rol']

class BitacoraSerializer(serializers.ModelSerializer):
    usuario = CustomUserForBitacoraSerializer(read_only=True) # Anida el serializador de usuario

    class Meta:
        model = Bitacora
        fields = '__all__'
        # O podrías especificar los campos para mayor control:
        # fields = ['id', 'login', 'logout', 'usuario', 'ip', 'device']

# serializers.py
from rest_framework import serializers
from .models import DispositivoMovil, NotificacionPush, IncidenteSeguridadIA

class DispositivoMovilSerializer(serializers.ModelSerializer):
    class Meta:
        model = DispositivoMovil
        fields = [
            'id', 'usuario', 'token_fcm', 'modelo_dispositivo',
            'sistema_operativo', 'activo', 'fecha_registro', 'ultima_conexion'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['usuario_username'] = instance.usuario.username if instance.usuario else None
        rep['usuario_nombre_completo'] = f"{instance.usuario.nombre} {instance.usuario.apellido_paterno}" if instance.usuario else None
        return rep


class NotificacionPushSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificacionPush
        fields = [
            'id', 'usuario', 'dispositivo', 'titulo', 'cuerpo', 'tipo',
            'estado', 'fecha_envio', 'fecha_entrega', 'fecha_lectura',
            'datos_adicionales', 'intento_envio'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['usuario_username'] = instance.usuario.username if instance.usuario else None
        rep['usuario_nombre_completo'] = f"{instance.usuario.nombre} {instance.usuario.apellido_paterno}" if instance.usuario else None
        rep['dispositivo_modelo'] = instance.dispositivo.modelo_dispositivo if instance.dispositivo else None
        rep['tipo_display'] = instance.get_tipo_display()
        rep['estado_display'] = instance.get_estado_display()
        return rep


class IncidenteSeguridadIASerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidenteSeguridadIA
        fields = [
            'id', 'tipo', 'descripcion', 'fecha_hora', 'ubicacion',
            'imagen_evidencia', 'notificacion_enviada', 'resuelto',
            'resuelto_por', 'fecha_resolucion'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['tipo_display'] = instance.get_tipo_display()
        rep['resuelto_por_username'] = instance.resuelto_por.username if instance.resuelto_por else None
        rep['resuelto_por_nombre'] = f"{instance.resuelto_por.nombre} {instance.resuelto_por.apellido_paterno}" if instance.resuelto_por else None
        rep['notificacion_id'] = instance.notificacion_enviada.id if instance.notificacion_enviada else None
        rep['notificacion_titulo'] = instance.notificacion_enviada.titulo if instance.notificacion_enviada else None
        return rep

class RegistroAccesoVehicularSerializer(serializers.ModelSerializer):
    # Añadir un campo para la placa del vehículo asociado
    vehiculo_autorizado_placa = serializers.SerializerMethodField()
    registrado_por_username = serializers.SerializerMethodField() # Si también lo obtienes así

    class Meta:
        model = RegistroAccesoVehicular
        fields = [
            'id',
            'placa_detectada',
            'acceso_exitoso',
            'fecha_hora_intento',
            'observaciones',
            'vehiculo_asociado', # Mantener el ID si es útil para otras cosas
            'vehiculo_autorizado_placa', # Nuevo campo
            'registrado_por_username', # Si es un campo custom
        ]
        read_only_fields = ['fecha_hora_intento', 'registrado_por_username'] # Si se generan automáticamente

    def get_vehiculo_autorizado_placa(self, obj):
        if obj.vehiculo_asociado:
            return obj.vehiculo_asociado.placa # Retorna la placa del vehículo
        return None # O una cadena vacía, según prefieras

    def get_registrado_por_username(self, obj):
        # Asumiendo que `request.user` está disponible en el contexto del serializer si el registro es hecho por un usuario
        # Si el usuario se guarda en el modelo RegistroAccesoVehicular, ajusta esto.
        # Por ahora, un placeholder ya que no se ve en tu modelo RegistroAccesoVehicular.
        return "Sistema" # o el nombre de usuario si lo tienes
