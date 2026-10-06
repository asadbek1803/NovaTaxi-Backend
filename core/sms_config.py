from django.conf import settings


def _get(key, default):
    return getattr(settings, key, default)


SMS_GATEWAY = {
    'IP': _get('SMS_GATEWAY_IP', '192.168.1.101'),
    'PORT': _get('SMS_GATEWAY_PORT', 8080),
    'ENDPOINT': _get('SMS_GATEWAY_ENDPOINT', '/send-sms'),
    'TIMEOUT': _get('SMS_GATEWAY_TIMEOUT', 5),
}

SMS_TEMPLATES = {
    'uz': "Nova Taxi: Sizning tasdiqlash kodingiz - {otp}. Kodni hech kimga bermang.",
    'ru': "Nova Taxi: Ваш код подтверждения - {otp}. Никому не сообщайте код.",
    'en': "Nova Taxi: Your verification code is {otp}. Do not share this code with anyone.",
}

SMS_DEFAULT_LANGUAGE = _get('SMS_DEFAULT_LANGUAGE', 'uz')
