import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.config import settings

logger = logging.getLogger("whatsapp_agent.whatsapp_client")

class WhatsAppClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v20.0"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    async def _send_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to send POST request to WhatsApp Graph API, falling back to simulator logs if credentials are empty."""
        if settings.is_simulated_whatsapp:
            logger.info(f"[SIMULATOR] Outgoing payload to Meta Graph API: {payload}")
            # Mock success response
            return {"messaging_product": "whatsapp", "contacts": [{"input": payload.get("to"), "wa_id": payload.get("to")}], "messages": [{"id": f"sim_msg_{datetime.utcnow().timestamp()}"}]}

        url = f"{self.base_url}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"WhatsApp API HTTP error: {e.response.text}")
                raise e
            except Exception as e:
                logger.error(f"WhatsApp API Connection error: {e}")
                raise e

    async def mark_as_read(self, customer_phone: str, message_id: str):
        """Sends read receipt for an inbound message."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        logger.info(f"Marking message {message_id} as read for {customer_phone}")
        return await self._send_request(payload)

    async def toggle_typing_indicator(self, customer_phone: str, is_active: bool = True):
        """Toggles the native typing indicator on/off."""
        # Meta's typing indicator API toggles based on the custom typing_indicator type
        # Page 2 specifies: POST /v20.0/<PHONE_NUMBER_ID>/messages with typing_indicator block
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": customer_phone,
            "type": "typing_indicator",
            "typing_indicator": {
                "type": "text"
            }
        }
        action = "starting" if is_active else "stopping"
        logger.info(f"WhatsApp: {action} typing indicator for {customer_phone}")
        
        # Note: If is_active is False, Meta's typing indicator automatically turns off 
        # when a regular text/media message is dispatched to the user. We will trigger the API POST.
        return await self._send_request(payload)

    async def send_text_message(self, customer_phone: str, text: str) -> Dict[str, Any]:
        """Dispatches a standard text message supporting Markdown formatting."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": customer_phone,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": True
            }
        }
        logger.info(f"Sending text message to {customer_phone}")
        return await self._send_request(payload)

    async def send_image_message(self, customer_phone: str, image_url: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches an image message via public URL."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": customer_phone,
            "type": "image",
            "image": {
                "link": image_url
            }
        }
        if caption:
            payload["image"]["caption"] = caption
            
        logger.info(f"Sending image ({image_url}) to {customer_phone}")
        return await self._send_request(payload)

    async def send_document_message(self, customer_phone: str, document_url: str, filename: str, caption: Optional[str] = None) -> Dict[str, Any]:
        """Dispatches a document/PDF message via public URL."""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": customer_phone,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename
            }
        }
        if caption:
            payload["document"]["caption"] = caption

        logger.info(f"Sending document ({filename} @ {document_url}) to {customer_phone}")
        return await self._send_request(payload)

whatsapp_client = WhatsAppClient()
