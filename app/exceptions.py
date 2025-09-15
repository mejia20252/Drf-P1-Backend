# app/exceptions.py
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    resp = exception_handler(exc, context)
    if resp is None:
        return resp
    # DRF suele devolver: {"detail":"..."} o {"field":["msg", ...]}
    payload = {
        "error": {
            "message": None,
            "code": getattr(getattr(exc, 'default_code', None), 'upper', lambda: None)() or "ERROR",
            "fields": {}
        }
    }
    data = resp.data
    print("data in exce.o",data)
    if "detail" in data:
        payload["error"]["message"] = data["detail"]
    else:
        # errores de validación por campo
        payload["error"]["message"] = "ERRORES EN EL BACKEND"
        payload["error"]["fields"] = data  # {campo: [mensajes]}

    resp.data = payload
    return resp

"""
{
  "usuario": {
    "username": [
      "A user with that username already exists."
    ],
    "email": [
      "user with this email already exists."
    ]
  }
}"""