import logging

import requests

from core.sms_config import SMS_GATEWAY, SMS_TEMPLATES, SMS_DEFAULT_LANGUAGE

logger = logging.getLogger('sms')


def build_sms_url():
    ip = SMS_GATEWAY['IP']
    port = SMS_GATEWAY['PORT']
    endpoint = SMS_GATEWAY['ENDPOINT']
    return f'http://{ip}:{port}{endpoint}'


def format_phone(phone):
    return phone.lstrip('+')


def send_sms_via_gateway(phone_number, otp_code, language=None):
    lang = language or SMS_DEFAULT_LANGUAGE
    template = SMS_TEMPLATES.get(lang, SMS_TEMPLATES[SMS_DEFAULT_LANGUAGE])
    message = template.format(otp=otp_code)

    formatted_phone = format_phone(phone_number)
    url = build_sms_url()

    payload = {
        'phone': formatted_phone,
        'message': message,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=SMS_GATEWAY['TIMEOUT'],
        )
        response.raise_for_status()
        logger.info(f'SMS sent to {formatted_phone} | Status: {response.status_code}')
        return True
    except requests.exceptions.ConnectionError:
        logger.error(f'SMS gateway unreachable: {url}')
        return False
    except requests.exceptions.Timeout:
        logger.error(f'SMS gateway timeout: {url}')
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f'SMS gateway HTTP error: {e}')
        return False
    except Exception as e:
        logger.error(f'SMS send failed: {e}')
        return False
