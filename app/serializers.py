from rest_framework import serializers
#login
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

#login
from .models import (
    Rol, Usuario, Telefono, Administrador, Personal, Cliente
)

# Serializer para el modelo Rol
class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = '__all__'

# Serializer para el modelo Usuario
# Nota: Aquí puedes decidir qué campos exponer. Excluir el 'password' es una buena práctica para la mayoría de las respuestas.
class UsuarioSerializer(serializers.ModelSerializer):
    rol=RolSerializer()
    class Meta:
        model = Usuario
        # Excluimos el 'password' por seguridad en las respuestas de la API
        fields = [
            'id', 'username', 'nombre', 'apellido_paterno', 'apellido_materno', 
            'email', 'direccion', 'fecha_nacimiento', 'rol'
        ]
        # Hacemos el campo 'password' de solo escritura para poderlo recibir al crear un usuario
        extra_kwargs = {'password': {'write_only': True, 'required': False}}

# Serializer para el moadelo Telefono
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

# Serializer para el modelo Cliente
class ClienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Cliente
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
    