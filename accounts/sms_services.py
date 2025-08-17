"""
SMS Service Integration using Twilio
"""

from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TwilioSMSService:
    """Twilio SMS Service Integration"""
    
    def __init__(self):
        try:
            from twilio.rest import Client
            self.account_sid = settings.TWILIO_ACCOUNT_SID
            self.auth_token = settings.TWILIO_AUTH_TOKEN
            self.from_number = settings.TWILIO_PHONE_NUMBER
            self.client = Client(self.account_sid, self.auth_token)
        except ImportError:
            logger.error("Twilio not installed. Run: pip install twilio")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {str(e)}")
            raise
    
    def send_sms(self, phone_number, message):
        """
        Send SMS using Twilio
        Args:
            phone_number: Phone number with country code (e.g., +1234567890)
            message: SMS message text
        Returns:
            Boolean indicating success/failure
        """
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            logger.info(f"SMS sent successfully to {phone_number}. SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False


class ConsoleSMSService:
    """Mock SMS service that prints to console (for development)"""
    
    def send_sms(self, phone_number, message):
        """
        Print SMS to console for development testing
        """
        print(f"\n{'='*50}")
        print(f"SMS to: {phone_number}")
        print(f"Message: {message}")
        print(f"{'='*50}\n")
        logger.info(f"SMS printed to console for {phone_number}")
        return True


def get_sms_service():
    """
    Factory function to get the configured SMS service
    Returns Twilio in production, Console in development
    """
    # Use Twilio if credentials are configured
    if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
        try:
            return TwilioSMSService()
        except Exception as e:
            logger.warning(f"Failed to initialize Twilio, falling back to console: {str(e)}")
            return ConsoleSMSService()
    else:
        # Use console service in development
        return ConsoleSMSService()