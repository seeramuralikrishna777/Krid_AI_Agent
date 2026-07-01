import hmac
import hashlib
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("whatsapp_agent.utils")

def verify_webhook_signature(body_bytes: bytes, signature_header: Optional[str]) -> bool:
    """
    Validates that the incoming HTTP request payload originates from Meta.
    Computes HMAC-SHA256 signature of request body using App Secret.
    """
    # If app secret is not configured, bypass verification for testing
    if not settings.WEBHOOK_APP_SECRET:
        logger.warning("WEBHOOK_APP_SECRET is not set. Bypassing payload signature verification.")
        return True
        
    if not signature_header:
        logger.error("Missing X-Hub-Signature-256 header.")
        return False
        
    if not signature_header.startswith("sha256="):
        logger.error("Invalid X-Hub-Signature-256 header format.")
        return False
        
    expected_sig = signature_header[7:]  # Strip 'sha256='
    
    try:
        computed_sig = hmac.new(
            settings.WEBHOOK_APP_SECRET.encode("utf-8"),
            body_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Timing-safe comparison to prevent timing attacks
        return hmac.compare_digest(computed_sig, expected_sig)
    except Exception as e:
        logger.error(f"Error validating webhook signature: {e}")
        return False
