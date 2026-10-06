import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger('sms')

FCM_URL = 'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
FCM_URL_LEGACY = 'https://fcm.googleapis.com/fcm/send'


def _get_access_token():
    try:
        from google.oauth2 import service_account
        creds_path = getattr(settings, 'FIREBASE_CREDENTIALS', None)
        if not creds_path:
            return None
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/firebase.messaging']
        )
        credentials.refresh(requests.Request())
        return credentials.token
    except Exception as e:
        logger.warning(f"FCM access token error: {e}")
        return None


def send_push_notification(tokens, title, body, data=None, image_url=None):
    if not tokens:
        return {'success': 0, 'failed': 0, 'errors': []}

    server_key = getattr(settings, 'FCM_SERVER_KEY', '')
    project_id = getattr(settings, 'FCM_PROJECT_ID', '')

    if not server_key and not project_id:
        logger.warning("FCM not configured (no FCM_SERVER_KEY or FCM_PROJECT_ID). Skipping push.")
        return {'success': 0, 'failed': len(tokens), 'errors': ['FCM not configured']}

    success_count = 0
    failed_count = 0
    errors = []

    if project_id:
        access_token = _get_access_token()
        if not access_token:
            return {'success': 0, 'failed': len(tokens), 'errors': ['Failed to get access token']}

        for token in tokens:
            payload = {
                'message': {
                    'token': token,
                    'notification': {
                        'title': title,
                        'body': body,
                    },
                    'data': {k: str(v) for k, v in (data or {}).items()},
                }
            }
            if image_url:
                payload['message']['notification']['image'] = image_url

            try:
                resp = requests.post(
                    FCM_URL.format(project_id=project_id),
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    timeout=5,
                )
                if resp.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{token[:20]}...: {resp.status_code}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{token[:20]}...: {str(e)}")
    else:
        headers = {
            'Authorization': f'key={server_key}',
            'Content-Type': 'application/json',
        }
        for token in tokens:
            payload = {
                'to': token,
                'notification': {
                    'title': title,
                    'body': body,
                },
                'data': data or {},
            }
            if image_url:
                payload['notification']['image'] = image_url

            try:
                resp = requests.post(
                    FCM_URL_LEGACY,
                    headers=headers,
                    json=payload,
                    timeout=5,
                )
                if resp.status_code == 200:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"{token[:20]}...: {resp.status_code}")
            except Exception as e:
                failed_count += 1
                errors.append(f"{token[:20]}...: {str(e)}")

    return {
        'success': success_count,
        'failed': failed_count,
        'errors': errors[:10],
    }
