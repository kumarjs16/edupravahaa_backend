from django.urls import path
from .views import CreateOrderView, VerifyPaymentView

app_name = 'payments'

urlpatterns = [
    path('create_order/', CreateOrderView.as_view(), name='create_order'),
    path('verify_payment/', VerifyPaymentView.as_view(), name='verify_payment'),
]