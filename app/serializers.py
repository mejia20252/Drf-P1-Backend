from django.db import models 
from rest_framework import serializers
#login
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
#login
from .models import (
    Rol, Usuario, Telefono, Administrador, Personal,   Bitacora, DetalleBitacora, Mascota, Propietario, Inquilino,
    Casa, AreaComun, Reserva, PagoReserva, TareaMantenimiento,
    Vehiculo, Residente
)
from django.contrib.auth.models import Group, Permission as AuthPermission

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

class UsuarioSerializer(serializers.ModelSerializer):
    # Campos adicionales según rol (solo para escritura)
    rol_nombre = serializers.CharField(write_only=True, required=True)
    #Inquilino    
    fecha_inicio_contrato = serializers.DateField(required=False, allow_null=True)
    fecha_fin_contrato = serializers.DateField(required=False, allow_null=True)

    fecha_adquisicion = serializers.DateField(required=False, allow_null=True)
    numero_licencia = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)
    tipo_personal = serializers.ChoiceField(choices=[
        'seguridad', 'mantenimiento', 'limpieza', 'jardineria'
    ], required=False, allow_null=True)
    fecha_ingreso = serializers.DateField(required=False, allow_null=True)
    salario = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    fecha_certificacion = serializers.DateField(required=False, allow_null=True)
    empresa = serializers.CharField(max_length=255, required=False, allow_null=True, allow_blank=True)
    # Para lectura: muestra el rol completo
    rol = RolSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'email', 'nombre', 'apellido_paterno', 'apellido_materno',
            'sexo', 'direccion', 'fecha_nacimiento', 'rol', 'rol_nombre',
            'fecha_inicio_contrato', 'fecha_fin_contrato',
            'fecha_adquisicion',
            'numero_licencia',
            'tipo_personal', 'fecha_ingreso', 'salario',
            'password',  # 👈 Incluye password aquí para CREATE
            'fecha_certificacion',
            'empresa',
           
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': False, 'allow_blank': True},
            'nombre': {'required': True},
            'apellido_paterno': {'required': True},
            'apellido_materno': {'required': True},
        }

    def validate(self, data):
        rol_nombre = data.get('rol_nombre')
        errors = {}

        # Verificar que el rol exista
        try:
            rol_obj = Rol.objects.get(nombre=rol_nombre)
            data['rol_obj'] = rol_obj
        except Rol.DoesNotExist:
            raise serializers.ValidationError({
                "rol_nombre": f"El rol '{rol_nombre}' no existe en el sistema."
            })

        # Validaciones específicas por rol
        if rol_nombre == "Inquilino":
            if not data.get('fecha_inicio_contrato'):
                errors['fecha_inicio_contrato'] = ['Este campo es obligatorio para Inquilinos.']
            if not data.get('fecha_fin_contrato'):
                errors['fecha_fin_contrato'] = ['Este campo es obligatorio para Inquilinos.']
            if data.get('fecha_inicio_contrato') and data.get('fecha_fin_contrato'):
                if data['fecha_fin_contrato'] < data['fecha_inicio_contrato']:
                    errors['fecha_fin_contrato'] = ['La fecha de fin no puede ser anterior a la de inicio.']

        elif rol_nombre == "Propietario":
            if not data.get('fecha_adquisicion'):
                errors['fecha_adquisicion'] = ['Este campo es obligatorio para Propietarios.']

        elif rol_nombre == "Administrador":
            if not data.get('numero_licencia') or not data['numero_licencia'].strip():
                errors['numero_licencia'] = ['Este campo es obligatorio para Administradores.']

        elif rol_nombre == "Personal":
            if not data.get('tipo_personal'):
                errors['tipo_personal'] = ['Este campo es obligatorio para Personal.']
            if not data.get('fecha_ingreso'):
                errors['fecha_ingreso'] = ['Este campo es obligatorio para Personal.']
            if data.get('salario') is not None and data['salario'] < 0:
                errors['salario'] = ['El salario no puede ser negativo.']

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        # Extraer campos dinámicos
        fecha_inicio_contrato = validated_data.pop('fecha_inicio_contrato', None)
        fecha_fin_contrato = validated_data.pop('fecha_fin_contrato', None)
        fecha_adquisicion = validated_data.pop('fecha_adquisicion', None)
        numero_licencia = validated_data.pop('numero_licencia', None)
        tipo_personal = validated_data.pop('tipo_personal', None)
        fecha_ingreso = validated_data.pop('fecha_ingreso', None)
        salario = validated_data.pop('salario', None)

        # Extraer el nombre del rol y obtener el objeto Rol
        rol_nombre = validated_data.pop('rol_nombre')
        rol_obj = validated_data.pop('rol_obj')

        # Crear usuario
        password = validated_data.pop('password')
        usuario = Usuario.objects.create_user(password=password, **validated_data)

        # Asignar rol
        usuario.rol = rol_obj
        usuario.save()

        # Crear modelo específico según rol
        if rol_nombre == "Inquilino":
            Inquilino.objects.create(
                usuario=usuario,
                fecha_inicio_contrato=fecha_inicio_contrato,
                fecha_fin_contrato=fecha_fin_contrato
            )
        elif rol_nombre == "Propietario":
            Propietario.objects.create(
                usuario=usuario,
                fecha_adquisicion=fecha_adquisicion
            )
        elif rol_nombre == "Administrador":
            Administrador.objects.create(
                usuario=usuario,
                numero_licencia=numero_licencia,
                fecha_certificacion=None
            )
        elif rol_nombre == "Personal":
            Personal.objects.create(
                usuario=usuario,
                tipo=tipo_personal,
                fecha_ingreso=fecha_ingreso,
                salario=salario
            )

        return usuario

    def update(self, instance, validated_data):
        # Evitar cambiar el rol después de creado
        if 'rol_nombre' in validated_data:
            raise serializers.ValidationError({"rol_nombre": "No se permite cambiar el rol después de la creación."})

        # Extraer campos dinámicos
        fecha_inicio_contrato = validated_data.pop('fecha_inicio_contrato', None)
        fecha_fin_contrato = validated_data.pop('fecha_fin_contrato', None)
        fecha_adquisicion = validated_data.pop('fecha_adquisicion', None)
        numero_licencia = validated_data.pop('numero_licencia', None)
        tipo_personal = validated_data.pop('tipo_personal', None)
        fecha_ingreso = validated_data.pop('fecha_ingreso', None)
        salario = validated_data.pop('salario', None)

        # Actualizar campos básicos
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar modelo específico según rol actual
        rol_nombre = instance.rol.nombre

        if rol_nombre == "Inquilino":
            inquilino, created = Inquilino.objects.get_or_create(usuario=instance)
            if fecha_inicio_contrato is not None:
                inquilino.fecha_inicio_contrato = fecha_inicio_contrato
            if fecha_fin_contrato is not None:
                inquilino.fecha_fin_contrato = fecha_fin_contrato
            inquilino.save()

        elif rol_nombre == "Propietario":
            propietario, created = Propietario.objects.get_or_create(usuario=instance)
            if fecha_adquisicion is not None:
                propietario.fecha_adquisicion = fecha_adquisicion
            propietario.save()

        elif rol_nombre == "Administrador":
            admin, created = Administrador.objects.get_or_create(usuario=instance)
            if numero_licencia is not None:
                admin.numero_licencia = numero_licencia
            admin.save()

        elif rol_nombre == "Personal":
            personal, created = Personal.objects.get_or_create(usuario=instance)
            if tipo_personal is not None:
                personal.tipo = tipo_personal
            if fecha_ingreso is not None:
                personal.fecha_ingreso = fecha_ingreso
            if salario is not None:
                personal.salario = salario
            personal.save()

        return instance


# Serializer para el modelo Usuario
# Nota: Aquí puedes decidir qué campos exponer. Excluir el 'password' es una buena práctica para la mayoría de las respuestas.

class TelefonoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Telefono
        fields = '__all__'

# Serializer para el modelo Administrador
class AdministradorSerializer(serializers.ModelSerializer):
    # Usamos el UsuarioSerializer como campo anidado para ver los detalles del usuario
    usuario = UsuarioSerializer()

    class Meta:
        model = Administrador
        fields = '__all__'

# Serializer para el modelo Personal
class PersonalSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Personal
        fields = '__all__'



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



# Serializer para el modelo Bitacora
class BitacoraSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)

    class Meta:
        model = Bitacora
        fields = '__all__'

# Serializer para el modelo DetalleBitacora
class DetalleBitacoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleBitacora
        fields = '__all__'

# Serializer para el modelo Mascota
class MascotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mascota
        fields = '__all__'

# serializers.py

# SERIALIZADOR ÚNICO Y CORRECTO PARA PROPIETARIO
class PropietarioSerializer(serializers.ModelSerializer):
    # Campo de escritura: ID del usuario al que se le asignará el rol de propietario
    usuario_id = serializers.IntegerField(write_only=True, required=True)

    # Campo de lectura: muestra los detalles completos del usuario
    usuario = UsuarioSerializer(read_only=True)

    class Meta:
        model = Propietario
        fields = ['id', 'usuario', 'usuario_id', 'fecha_adquisicion']
        extra_kwargs = {
            'fecha_adquisicion': {'required': False, 'allow_null': True},
        }

    def validate_usuario_id(self, value):
        """Validar que el usuario exista y no sea ya propietario."""
        try:
            usuario = Usuario.objects.get(id=value)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("El usuario con este ID no existe.")

        # Verificar que no sea ya propietario
        if hasattr(usuario, 'propietario'):
            raise serializers.ValidationError("Este usuario ya es propietario.")

        # Verificar que no tenga otro rol activo que impida ser propietario
        if usuario.rol and usuario.rol.nombre in ['Administrador', 'Personal']:
            raise serializers.ValidationError(
                f"El usuario tiene rol '{usuario.rol.nombre}' y no puede ser propietario."
            )

        return value

    def create(self, validated_data):
        usuario_id = validated_data.pop('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)

        try:
            rol_propietario = Rol.objects.get(nombre="Propietario")
        except Rol.DoesNotExist:
            raise serializers.ValidationError({
                "usuario_id": "El rol 'Propietario' no está configurado en el sistema. Contacte al administrador."
            })

        usuario.rol = rol_propietario
        usuario.save(update_fields=['rol'])

        propietario = Propietario.objects.create(usuario=usuario, **validated_data)

        Residente.objects.get_or_create(
            usuario=usuario,
            casa=None,
            rol_residencia='propietario',
            defaults={'fecha_mudanza': timezone.now()}
        )

        return propietario

    def update(self, instance, validated_data):
        if 'usuario_id' in validated_data:
            raise serializers.ValidationError({"usuario_id": "No se puede cambiar el usuario después de la creación."})

        instance.fecha_adquisicion = validated_data.get('fecha_adquisicion', instance.fecha_adquisicion)
        instance.save()
        return instance
# Serializer para el modelo Residente
class ResidenteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(read_only=True)
    casa = serializers.SerializerMethodField()

    class Meta:
        model = Residente
        fields = '__all__'
    
class CasaSerializer(serializers.ModelSerializer):
    # Solo muestra el propietario como objeto anidado (lectura)
    propietario = PropietarioSerializer(read_only=True)

    class Meta:
        model = Casa
        fields = [
            'id',
            'numero_casa',
            'tipo_de_unidad',
            'numero',
            'area',
            'propietario'
        ]
        extra_kwargs = {
            'numero_casa': {'required': True},
            'tipo_de_unidad': {'required': True},
            'numero': {'required': True},
            'area': {'required': True},
        }

    # Elimina cualquier validación o lógica relacionada con 'propietario_nombre'
    # Ya no necesitamos eso aquí, porque no vamos a asignar propietarios desde este serializer
    def validate(self, data):
        propietario_nombre = data.get('propietario_nombre')
        if propietario_nombre:
            # Validar que exista un Propietario con ese nombre o email
            try:
                usuario = Usuario.objects.filter(
                    models.Q(nombre__icontains=propietario_nombre) |
                    models.Q(email__iexact=propietario_nombre)
                ).get()
                propietario = Propietario.objects.get(usuario=usuario)
                data['propietario_obj'] = propietario
            except Usuario.DoesNotExist:
                raise serializers.ValidationError({
                    "propietario_nombre": f"No se encontró ningún usuario con nombre o email '{propietario_nombre}'."
                })
            except Propietario.DoesNotExist:
                raise serializers.ValidationError({
                    "propietario_nombre": f"El usuario '{propietario_nombre}' existe, pero no es un Propietario."
                })
        return data

    def create(self, validated_data):
        # Extraer el propietario si se envió
        propietario_obj = validated_data.pop('propietario_obj', None)

        # Crear la casa (sin propietario aún)
        casa = Casa.objects.create(**validated_data)

        # Si se proporcionó un propietario, asignarlo y crear Residente
        if propietario_obj:
            casa.propietario = propietario_obj
            casa.save()

            # ✅ CREAR RESIDENTE (¡Importante! Mantén coherencia de datos)
            Residente.objects.get_or_create(
                usuario=propietario_obj.usuario,
                casa=casa,
                rol_residencia='propietario',
                defaults={'fecha_mudanza': timezone.now()}
            )

        return casa

    def update(self, instance, validated_data):
        propietario_nombre = validated_data.pop('propietario_nombre', None)

        if propietario_nombre:
            try:
                usuario = Usuario.objects.filter(
                    models.Q(nombre__icontains=propietario_nombre) |
                    models.Q(email__iexact=propietario_nombre)
                ).get()
                propietario = Propietario.objects.get(usuario=usuario)

                # Actualizar propietario de la casa
                instance.propietario = propietario
                instance.save()

                # Actualizar o crear Residente
                residente, created = Residente.objects.get_or_create(
                    usuario=propietario.usuario,
                    casa=instance,
                    defaults={
                        'rol_residencia': 'propietario',
                        'fecha_mudanza': timezone.now()
                    }
                )
                if not created:
                    residente.rol_residencia = 'propietario'
                    residente.save()

            except Usuario.DoesNotExist:
                raise serializers.ValidationError({
                    "propietario_nombre": f"Usuario '{propietario_nombre}' no encontrado."
                })
            except Propietario.DoesNotExist:
                raise serializers.ValidationError({
                    "propietario_nombre": f"El usuario '{propietario_nombre}' no es un propietario registrado."
                })

        # Actualizar campos normales de Casa
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance





# Serializer para el modelo Inquilino
# app/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Inquilino, Usuario, Rol

# Obtener el modelo de usuario activo
User = get_user_model()


class AreaComunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaComun
        fields = '__all__'

# Serializer para el modelo Reserva
class ReservaSerializer(serializers.ModelSerializer):
    area_comun = AreaComunSerializer(read_only=True)
    usuario = UsuarioSerializer(read_only=True)

    class Meta:
        model = Reserva
        fields = '__all__'

# Serializer para el modelo PagoReserva
class PagoReservaSerializer(serializers.ModelSerializer):
    reserva = ReservaSerializer(read_only=True)

    class Meta:
        model = PagoReserva
        fields = '__all__'

# Serializer para el modelo TareaMantenimiento
class TareaMantenimientoSerializer(serializers.ModelSerializer):
    administrador_asigna = AdministradorSerializer(read_only=True)
    personal_asignado = PersonalSerializer(read_only=True)
    casa = CasaSerializer(read_only=True)
    area_comun = AreaComunSerializer(read_only=True)

    class Meta:
        model = TareaMantenimiento
        fields = '__all__'

# serializers.py

# serializers.py - Actualiza VehiculoSerializer
class VehiculoSerializer(serializers.ModelSerializer):
    # Para escritura: aceptamos el ID del usuario
    dueno_id = serializers.IntegerField(write_only=True, required=True)
    
    # Para lectura: mostramos los detalles completos
    dueno = UsuarioSerializer(read_only=True)
    casa = CasaSerializer(read_only=True)

    class Meta:
        model = Vehiculo
        fields = [
            'id',
            'placa',
            'tipo',
            'dueno',
            'casa',
            'dueno_id'  # 👈 Incluido aquí
        ]
        extra_kwargs = {
            'placa': {'required': True},
            'tipo': {'required': True},
        }

    def create(self, validated_data):
        dueno_id = validated_data.pop('dueno_id')
        usuario = Usuario.objects.get(id=dueno_id)
        vehiculo = Vehiculo.objects.create(
            dueno=usuario,
            **validated_data
        )
        return vehiculo

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




# serializers.py

class AsignarPropietarioACasaSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField(write_only=True, required=True)

    def validate_usuario_id(self, value):
        try:
            usuario = Usuario.objects.get(id=value)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("El usuario con este ID no existe.")

        if not hasattr(usuario, 'propietario'):
            raise serializers.ValidationError("Este usuario no es un propietario registrado.")

        return value

    def save(self, **kwargs):
        casa = kwargs['casa']  # Lo pasamos desde la vista
        usuario_id = self.validated_data['usuario_id']
        usuario = Usuario.objects.get(id=usuario_id)
        propietario = usuario.propietario

        casa.propietario = propietario
        casa.save()

        # Asegurar que exista el Residente
        Residente.objects.get_or_create(
            usuario=usuario,
            casa=casa,
            rol_residencia='propietario',
            defaults={'fecha_mudanza': timezone.now()}
        )

        return casa
# serializers.py

class AsignarCasaAVehiculoSerializer(serializers.Serializer):
    casa_id = serializers.IntegerField(write_only=True, required=True)

    def validate_casa_id(self, value):
        try:
            casa = Casa.objects.get(id=value)
        except Casa.DoesNotExist:
            raise serializers.ValidationError("La casa con este ID no existe.")

        # Opcional: Validar que la casa tenga un residente asociado al usuario dueño del vehículo
        # Esto evita asignar vehículos a casas sin residentes
        if not Residente.objects.filter(casa=casa).exists():
            raise serializers.ValidationError(
                "La casa no tiene ningún residente registrado. No se puede asignar un vehículo a una casa sin residente."
            )

        return value

    def save(self, **kwargs):
        vehiculo = kwargs['vehiculo']  # Pasado desde la vista
        casa_id = self.validated_data['casa_id']
        casa = Casa.objects.get(id=casa_id)

        vehiculo.casa = casa
        vehiculo.save()

        return vehiculo    
class AsignarCasaAInquilinoSerializer(serializers.Serializer):
    casa_id = serializers.IntegerField(write_only=True, required=True)

    def validate_casa_id(self, value):
        try:
            casa = Casa.objects.get(id=value)
        except Casa.DoesNotExist:
            raise serializers.ValidationError("La casa con este ID no existe.")
        
        # Opcional: Validar que la casa no tenga ya un propietario
        if casa.propietario:
            raise serializers.ValidationError("Esta casa ya tiene un propietario asignado.")

        return value

    def save(self, **kwargs):
        inquilino = kwargs['inquilino']  # Pasado desde la vista
        casa_id = self.validated_data['casa_id']
        casa = Casa.objects.get(id=casa_id)

        # Actualizar la relación en el modelo Inquilino (opcional, si lo deseas)
        # Puedes agregar un campo `casa` en Inquilino si lo necesitas
        # Pero por ahora, solo actualizamos el Residente

        # ✅ ACTUALIZAR EL RESIDENTE ASOCIADO AL USUARIO
        residente, created = Residente.objects.get_or_create(
            usuario=inquilino.usuario,
            defaults={
                'casa': casa,
                'rol_residencia': 'inquilino',
                'fecha_mudanza': timezone.now()
            }
        )

        if not created:
            residente.casa = casa
            residente.rol_residencia = 'inquilino'
            residente.save()

        return residente
class InquilinoSerializer(serializers.ModelSerializer):
    # Campo de escritura: ID del usuario que será inquilino
    usuario_id = serializers.IntegerField(write_only=True, required=True)

    # Campo de lectura: muestra los detalles completos del usuario
    usuario = UsuarioSerializer(read_only=True)

    class Meta:
        model = Inquilino
        fields = ['id', 'usuario', 'usuario_id', 'fecha_inicio_contrato', 'fecha_fin_contrato']
        extra_kwargs = {
            'fecha_inicio_contrato': {'required': True},
            'fecha_fin_contrato': {'required': True},
        }

    def validate_usuario_id(self, value):
        try:
            usuario = Usuario.objects.get(id=value)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("El usuario con este ID no existe.")

        # Verificar que no sea ya inquilino
        if hasattr(usuario, 'inquilino'):
            raise serializers.ValidationError("Este usuario ya es inquilino.")

        # Verificar que no tenga otro rol activo que impida ser inquilino
        if usuario.rol and usuario.rol.nombre in ['Administrador', 'Personal']:
            raise serializers.ValidationError(
                f"El usuario tiene rol '{usuario.rol.nombre}' y no puede ser inquilino."
            )

        return value

    def create(self, validated_data):
        usuario_id = validated_data.pop('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)

        try:
            rol_inquilino = Rol.objects.get(nombre="Inquilino")
        except Rol.DoesNotExist:
            raise serializers.ValidationError({
                "usuario_id": "El rol 'Inquilino' no está configurado en el sistema. Contacte al administrador."
            })

        usuario.rol = rol_inquilino
        usuario.save(update_fields=['rol'])

        inquilino = Inquilino.objects.create(usuario=usuario, **validated_data)

        # ✅ ¡CREAR RESIDENTE AL CREAR INQUILINO!
        # Aunque aún no tenga casa, lo creamos con casa=None
        Residente.objects.get_or_create(
            usuario=usuario,
            casa=None,
            rol_residencia='inquilino',
            defaults={'fecha_mudanza': timezone.now()}
        )

        return inquilino

    def update(self, instance, validated_data):
        if 'usuario_id' in validated_data:
            raise serializers.ValidationError({"usuario_id": "No se puede cambiar el usuario después de la creación."})

        instance.fecha_inicio_contrato = validated_data.get('fecha_inicio_contrato', instance.fecha_inicio_contrato)
        instance.fecha_fin_contrato = validated_data.get('fecha_fin_contrato', instance.fecha_fin_contrato)
        instance.save()

        return instance    
class AsignarResidenteACasaSerializer(serializers.Serializer):
    usuario_id = serializers.IntegerField(write_only=True, required=True)
    rol_residencia = serializers.ChoiceField(choices=Residente.ROL_RESIDENCIA_CHOICES)

    def validate_usuario_id(self, value):
        try:
            usuario = Usuario.objects.get(id=value)
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("El usuario no existe.")
        return value

    def save(self, **kwargs):
        casa = kwargs['casa']
        usuario_id = self.validated_data['usuario_id']
        rol = self.validated_data['rol_residencia']

        residente, created = Residente.objects.get_or_create(
            usuario_id=usuario_id,
            casa=casa,
            defaults={
                'rol_residencia': rol,
                'fecha_mudanza': timezone.now()
            }
        )

        if not created:
            residente.rol_residencia = rol
            residente.save()

        return residente