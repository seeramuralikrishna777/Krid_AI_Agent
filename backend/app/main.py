import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import db_manager
from app.models import BroadcastRequest, SimulatedMessageInput
from app.whatsapp_client import whatsapp_client
from app.agent import agent_graph, AgentState
from app.utils import verify_webhook_signature

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("whatsapp_agent.main")

# FastAPI App
app = FastAPI(
    title="Multi-Tenant Agentic WhatsApp Orchestrator API",
    description="Backend service powered by LangGraph, FastAPI, and MongoDB"
)

# CORS Middleware (Allow dashboard to call APIs locally during dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to dynamically detect public base URL from incoming requests
@app.middleware("http")
async def detect_public_url_middleware(request: Request, call_next):
    if not settings.PUBLIC_URL:
        base_url_str = str(request.base_url).rstrip("/")
        if "127.0.0.1" not in base_url_str and "localhost" not in base_url_str:
            settings.PUBLIC_URL = base_url_str
            logger.info(f"Dynamically detected public base URL from request: {settings.PUBLIC_URL}")
    response = await call_next(request)
    return response

# Initialize DB on Startup
@app.on_event("startup")
async def startup_db_client():
    await db_manager.connect()

# Asynchronous LangGraph Runner Helper
async def execute_agent_loop(tenant_id: str, customer_phone: str, inbound_msg: Dict[str, Any]):
    """Runs the LangGraph orchestration flow in the background."""
    # Resolve tenant_id dynamically from DB if not provided (from real webhook intake)
    if not tenant_id:
        try:
            cursor = db_manager.db.sessions.find({"customer_phone": customer_phone})
            cursor.sort("updated_at", -1).limit(1)
            sessions_list = await cursor.to_list(length=1)
            if sessions_list:
                tenant_id = sessions_list[0].get("tenant_id")
                logger.info(f"Dynamically routed real webhook message to tenant: {tenant_id}")
        except Exception as e:
            logger.error(f"Error searching tenant in DB: {e}")
        
        # Default fallback if no session exists yet
        if not tenant_id:
            tenant_id = "tenant_a"
            logger.info(f"No existing session found for {customer_phone}. Defaulting real webhook to tenant: {tenant_id}")

    session_id = f"{tenant_id}_{customer_phone}"
    logger.info(f"Kicking off LangGraph flow for session {session_id}")
    
    # Initialize State
    initial_state = AgentState(
        tenant_id=tenant_id,
        customer_phone=customer_phone,
        session_id=session_id,
        inbound_message=inbound_msg,
        chat_history=[],
        system_prompt="",
        media_library={},
        suggested_reply={},
        session_status="WAITING_FOR_BOT",
        sentiment_score=3.0,
        node_trace=[]
    )
    
    try:
        # Execute LangGraph compile run
        final_state = await agent_graph.ainvoke(initial_state)
        
        # Save the LangGraph node trace to the session context so the UI can retrieve it
        await db_manager.db.sessions.update_one(
            {"_id": session_id},
            {
                "$set": {
                    "context_variables.last_trace": final_state["node_trace"],
                    "context_variables.last_reply": final_state["suggested_reply"]
                }
            }
        )
        logger.info(f"LangGraph execution finished successfully. Trace: {final_state['node_trace']}")
    except Exception as e:
        logger.error(f"Error executing LangGraph agent loop: {e}", exc_info=True)
        # Clear typing indicator in case of failure
        try:
            await whatsapp_client.toggle_typing_indicator(customer_phone, is_active=False)
        except Exception:
            pass

# 1. Meta Webhook Challenge Verification (GET)
@app.get("/api/webhooks/whatsapp")
async def verify_webhook(
    request: Request,
    mode: str = Query(None, alias="hub.mode"),
    challenge: str = Query(None, alias="hub.challenge"),
    verify_token: str = Query(None, alias="hub.verify_token")
):
    """Handles Meta's Webhook verification challenge request."""
    logger.info(f"Received webhook verification challenge. Token: {verify_token}")
    if mode == "subscribe" and verify_token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verification challenge successful.")
        return Response(content=challenge, media_type="text/plain")
    else:
        logger.error("Webhook verification challenge failed.")
        raise HTTPException(status_code=403, detail="Verification token mismatch")

# 2. Meta Webhook Inbound Payload Intake (POST)
@app.post("/api/webhooks/whatsapp")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Receives incoming message payloads from Meta WhatsApp Cloud API."""
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # 1. Security validation
    if not verify_webhook_signature(body_bytes, signature):
        logger.error("Webhook payload signature validation failed.")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info(f"Received webhook event: {payload}")

    # 2. Parse Meta WhatsApp Payload Structure
    # Nested properties: entry -> changes -> value -> messages / statuses
    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            
            # Handle Outbound Status Updates (Read Receipts, Delivery receipts)
            statuses = value.get("statuses", [])
            for status_item in statuses:
                msg_id = status_item.get("id")
                status_val = status_item.get("status")  # sent, delivered, read, failed
                logger.info(f"Received Meta status callback: Message {msg_id} status is now '{status_val}'")
                await db_manager.db.messages.update_one(
                    {"_id": msg_id},
                    {"$set": {"status": status_val}}
                )

            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
            
            # Ensure message is meant for this phone number ID if set
            if settings.WHATSAPP_PHONE_NUMBER_ID and phone_number_id != settings.WHATSAPP_PHONE_NUMBER_ID:
                continue

            for msg in messages:
                customer_phone = msg.get("from")
                msg_id = msg.get("id")
                
                # Check message type
                msg_type = msg.get("type", "text")
                content = ""
                media_url = None
                mime_type = None
                filename = None
                
                if msg_type == "text":
                    content = msg.get("text", {}).get("body", "")
                elif msg_type == "image":
                    image_data = msg.get("image", {})
                    # Meta gives media ID. Real implementation requires fetching binary via Graph API.
                    # We store media ID as public URL simulation, or download.
                    media_url = f"https://graph.facebook.com/v20.0/{image_data.get('id')}/media" 
                    mime_type = image_data.get("mime_type")
                    content = "[Sent Image]"
                elif msg_type == "document":
                    doc_data = msg.get("document", {})
                    media_url = f"https://graph.facebook.com/v20.0/{doc_data.get('id')}/media"
                    mime_type = doc_data.get("mime_type")
                    filename = doc_data.get("filename")
                    content = f"[Sent Document: {filename}]"
                else:
                    # Skip other message types for prototype
                    continue

                inbound_msg = {
                    "id": msg_id,
                    "type": msg_type,
                    "content": content,
                    "media_url": media_url,
                    "mime_type": mime_type,
                    "filename": filename,
                    "timestamp": datetime.fromtimestamp(int(msg.get("timestamp", datetime.now(timezone.utc).timestamp())), tz=timezone.utc)
                }

                # We map incoming Meta message to the appropriate tenant.
                # Route to None first so execute_agent_loop resolves it from DB or defaults.
                tenant_id = None
                
                # Trigger LangGraph flow in background (Critical Async requirement)
                background_tasks.add_task(
                    execute_agent_loop,
                    tenant_id=tenant_id,
                    customer_phone=customer_phone,
                    inbound_msg=inbound_msg
                )

    # Respond to Meta immediately within 3s
    return {"status": "accepted"}

# 3. Fetch Tenants
@app.get("/api/tenants")
async def get_tenants():
    cursor = db_manager.db.tenants.find()
    return await cursor.to_list(length=100)

# 4. Fetch Active Sessions for a Tenant
@app.get("/api/sessions")
async def get_sessions(tenant_id: str):
    cursor = db_manager.db.sessions.find({"tenant_id": tenant_id})
    return await cursor.to_list(length=100)

# 5. Fetch Message Logs for a Session
@app.get("/api/messages")
async def get_messages(session_id: str):
    cursor = db_manager.db.messages.find({"session_id": session_id})
    cursor.sort("timestamp", 1)  # Ascending chronological order
    return await cursor.to_list(length=200)

# Simulated Status Lifecycle scheduler for Sandbox mode
async def simulate_message_status_lifecycle(message_id: str):
    """Simulates the sent -> delivered -> read status progression for sandbox messages."""
    try:
        await asyncio.sleep(1.0)
        await db_manager.db.messages.update_one({"_id": message_id}, {"$set": {"status": "delivered"}})
        await asyncio.sleep(2.0)
        await db_manager.db.messages.update_one({"_id": message_id}, {"$set": {"status": "read"}})
        logger.info(f"Simulated read receipt lifecycle completed for broadcast message: {message_id}")
    except Exception as e:
        logger.error(f"Error in simulated read receipt lifecycle for broadcast message {message_id}: {e}")

# 6. Campaign Broadcast Dispatch
@app.post("/api/broadcast")
async def trigger_broadcast(request: BroadcastRequest, background_tasks: BackgroundTasks):
    tenant = await db_manager.db.tenants.find_one({"_id": request.tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    broadcast_template = {
        "new_catalog_promo": {
            "type": "document",
            "content": "Hello! Check out our brand new catalog with special discounts!",
            "media_key": "catalog"
        },
        "service_reminder": {
            "type": "document",
            "content": "Hi! Just a reminder to verify your invoice and diagram for the scheduled appointment.",
            "media_key": "invoice"
        }
    }
    
    template = broadcast_template.get(request.template_name)
    if not template:
        raise HTTPException(status_code=400, detail="Invalid template name")
        
    media_key = template["media_key"]
    media_item = tenant.get("media_library", {}).get(media_key, {})
    
    reply = {
        "type": media_item.get("type", "text"),
        "content": request.custom_message or template["content"],
        "media_url": media_item.get("url"),
        "filename": media_item.get("filename")
    }

    # Queue up sending broadcast to each number in the background
    for num in request.numbers:
        session_id = f"{request.tenant_id}_{num}"
        
        # 1. Register Session if not exists
        await db_manager.db.sessions.update_one(
            {"_id": session_id},
            {
                "$set": {
                    "tenant_id": request.tenant_id,
                    "customer_phone": num,
                    "status": "AGENT_RESPONDING",
                    "updated_at": datetime.now(timezone.utc)
                }
            },
            upsert=True
        )
        
        # 2. Dispatch via WhatsApp Graph API in background and then log the message
        async def send_broadcast_task(num_val=num, reply_val=reply, s_id=session_id, t_id=request.tenant_id):
            try:
                response = None
                if reply_val["type"] == "image":
                    response = await whatsapp_client.send_image_message(num_val, reply_val["media_url"], reply_val["content"])
                elif reply_val["type"] == "document":
                    response = await whatsapp_client.send_document_message(num_val, reply_val["media_url"], reply_val["filename"], reply_val["content"])
                else:
                    response = await whatsapp_client.send_text_message(num_val, reply_val["content"])
                
                final_msg_id = f"broad_{datetime.now(timezone.utc).timestamp()}_{num_val}"
                if response and "messages" in response and len(response["messages"]) > 0:
                    final_msg_id = response["messages"][0]["id"]
                
                # Append message log here with final ID and status: "sent"
                await db_manager.db.messages.insert_one({
                    "_id": final_msg_id,
                    "session_id": s_id,
                    "tenant_id": t_id,
                    "customer_phone": num_val,
                    "direction": "outbound",
                    "type": reply_val["type"],
                    "content": reply_val["content"],
                    "media_url": reply_val["media_url"],
                    "filename": reply_val["filename"],
                    "status": "sent",
                    "timestamp": datetime.now(timezone.utc)
                })

                if settings.is_simulated_whatsapp:
                    asyncio.create_task(simulate_message_status_lifecycle(final_msg_id))
            except Exception as ex:
                logger.error(f"Failed to dispatch broadcast to {num_val}: {ex}")
                
        background_tasks.add_task(send_broadcast_task)
        
    return {"status": "broadcast_queued", "count": len(request.numbers)}

# 7. Simulator Inbound Message Endpoint (POST)
@app.post("/api/simulate/incoming")
async def simulate_incoming_message(
    input_data: SimulatedMessageInput,
    background_tasks: BackgroundTasks
):
    """Simulates an incoming user webhook event directly from the dashboard."""
    customer_phone = input_data.customer_phone
    tenant_id = input_data.tenant_id
    
    simulated_msg_id = f"sim_{datetime.now(timezone.utc).timestamp()}"
    
    inbound_msg = {
        "id": simulated_msg_id,
        "type": input_data.type,
        "content": input_data.content,
        "media_url": input_data.media_url,
        "mime_type": input_data.mime_type,
        "filename": input_data.filename,
        "timestamp": datetime.now(timezone.utc)
    }
    
    # Save the incoming message log to DB
    session_id = f"{tenant_id}_{customer_phone}"
    
    # Check if session exists to see if we should reset Needs Human handover
    # If the user simulates a message, we can let them converse.
    session = await db_manager.db.sessions.find_one({"_id": session_id})
    if session and session.get("status") == "NEEDS_HUMAN":
        # Reset Needs Human status for simulation/re-testing if they send another message
        await db_manager.db.sessions.update_one(
            {"_id": session_id},
            {"$set": {"status": "WAITING_FOR_BOT"}}
        )

    await db_manager.db.sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "tenant_id": tenant_id,
                "customer_phone": customer_phone,
                "updated_at": datetime.now(timezone.utc)
            },
            "$setOnInsert": {
                "status": "WAITING_FOR_BOT",
                "sentiment_score": 3.0,
                "context_variables": {}
            }
        },
        upsert=True
    )
    
    await db_manager.db.messages.insert_one({
        "_id": simulated_msg_id,
        "session_id": session_id,
        "tenant_id": tenant_id,
        "customer_phone": customer_phone,
        "direction": "inbound",
        "type": input_data.type,
        "content": input_data.content,
        "media_url": input_data.media_url,
        "mime_type": input_data.mime_type,
        "filename": input_data.filename,
        "timestamp": datetime.now(timezone.utc),
        "status": "read"
    })
    
    # Kick off LangGraph agent loop in background thread
    background_tasks.add_task(
        execute_agent_loop,
        tenant_id=tenant_id,
        customer_phone=customer_phone,
        inbound_msg=inbound_msg
    )
    
    return {"status": "queued", "message_id": simulated_msg_id}

# Mount static files dynamically if the directory exists
media_static_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.exists(media_static_path):
    app.mount("/static", StaticFiles(directory=media_static_path), name="media_static")
    logger.info(f"Mounted media static files from: {media_static_path}")

dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")
    logger.info(f"Mounted static frontend from: {dist_path}")
else:
    logger.warning(f"Static files directory {dist_path} does not exist. Frontend must be served separately.")
