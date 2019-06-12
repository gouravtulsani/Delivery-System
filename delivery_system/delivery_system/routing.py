from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from django.conf.urls import url
from delivery.consumers import DeliveryConsumer
from channels.auth import AuthMiddlewareStack

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter([
                url(r"^ws/$", DeliveryConsumer)
        ])
    )
})
