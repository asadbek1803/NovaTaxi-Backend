from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_codes = {
            400: 'VALIDATION_ERROR',
            401: 'UNAUTHORIZED',
            403: 'FORBIDDEN',
            404: 'NOT_FOUND',
            409: 'CONFLICT',
            429: 'RATE_LIMITED',
        }
        code = error_codes.get(response.status_code, 'ERROR')
        message = ''
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                message = str(response.data['detail'])
            else:
                message = str(response.data)
        elif isinstance(response.data, list):
            message = str(response.data[0]) if response.data else 'Xatolik'
        else:
            message = str(response.data)

        return Response({
            'success': False,
            'error': {
                'code': code,
                'message': message,
            }
        }, status=response.status_code)

    return Response({
        'success': False,
        'error': {
            'code': 'SERVER_ERROR',
            'message': 'Server xatosi',
        }
    }, status=500)
