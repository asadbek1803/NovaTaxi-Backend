from rest_framework.response import Response


def success_response(data=None, message=None, status_code=200):
    resp = {'success': True}
    if data is not None:
        resp['data'] = data
    if message is not None:
        resp['message'] = message
    return Response(resp, status=status_code)


def error_response(code, message, status_code=400):
    return Response({
        'success': False,
        'error': {
            'code': code,
            'message': message,
        }
    }, status=status_code)


def calc_distance(lat1, lng1, lat2, lng2):
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.asin(math.sqrt(a))
