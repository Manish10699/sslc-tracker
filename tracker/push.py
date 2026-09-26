import json
import os

from pywebpush import webpush, WebPushException

from .models import PushSubscription


def send_push_notification(user, title, message):
    subscriptions = PushSubscription.objects.filter(user=user)

    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
            },
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({
                    "title": title,
                    "body": message,
                }),
                vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY_PATH"),
                vapid_claims = {
    "sub": f"mailto:{os.getenv('VAPID_CLAIMS_EMAIL')}",
},
            )

        except WebPushException as e:
            print(f"Push notification failed: {e}")