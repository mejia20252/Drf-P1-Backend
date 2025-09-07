# permissions.py
from rest_framework import permissions

class IsAdministrador(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class IsCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Cliente'

class IsPersonal(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.rol.nombre == 'Personal'        