from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/signal/(?P<room_id>\w+)/$', consumers.WebRTCSignalingConsumer.as_asgi()),
]