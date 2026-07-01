import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.config import settings
from app.database import db_manager
from app.whatsapp_client import whatsapp_client

logger = logging.getLogger("whatsapp_agent.agent")

# Define LangGraph State Schema
class AgentState(TypedDict):
    tenant_id: str
    customer_phone: str
    session_id: str
    inbound_message: Dict[str, Any]
    chat_history: List[Dict[str, Any]]
    system_prompt: str
    media_library: Dict[str, Any]
    suggested_reply: Dict[str, Any]  # { "type": "text"|"image"|"document", "content": str, "media_url": str, "filename": str }
    session_status: str
    sentiment_score: float
    node_trace: List[str]

# ----------------- Nodes -----------------

async def acknowledge_node(state: AgentState) -> AgentState:
    """Node 1: Instantly fires read receipt & typing indicator, sets DB state to PENDING_RESPONSE."""
    state["node_trace"].append("Acknowledge Node")
    customer_phone = state["customer_phone"]
    inbound_msg = state["inbound_message"]
    
    # 1. Fire Read Receipt (if we have a real WhatsApp message ID)
    msg_id = inbound_msg.get("id")
    if msg_id and not msg_id.startswith("sim_"):
        try:
            await whatsapp_client.mark_as_read(customer_phone, msg_id)
        except Exception as e:
            logger.error(f"Failed to send read receipt: {e}")
            
    # 2. Fire Typing Indicator
    try:
        await whatsapp_client.toggle_typing_indicator(customer_phone, is_active=True)
    except Exception as e:
        logger.error(f"Failed to send typing indicator: {e}")
        
    # 3. Update session status in DB
    session_id = state["session_id"]
    await db_manager.db.sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "status": "WAITING_FOR_BOT",
                "updated_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
    
    # Save the incoming message if it isn't already logged
    await db_manager.db.messages.update_one(
        {"_id": msg_id},
        {
            "$setOnInsert": {
                "session_id": session_id,
                "tenant_id": state["tenant_id"],
                "customer_phone": customer_phone,
                "direction": "inbound",
                "type": inbound_msg.get("type", "text"),
                "content": inbound_msg.get("content", ""),
                "media_url": inbound_msg.get("media_url"),
                "mime_type": inbound_msg.get("mime_type"),
                "filename": inbound_msg.get("filename"),
                "timestamp": inbound_msg.get("timestamp", datetime.now(timezone.utc))
            }
        },
        upsert=True
    )

    state["session_status"] = "WAITING_FOR_BOT"
    return state

async def context_retriever_node(state: AgentState) -> AgentState:
    """Node 2: Pulls Tenant details and last 5 chat messages from DB."""
    state["node_trace"].append("Context Retriever Node")
    
    # 1. Fetch Tenant settings
    tenant = await db_manager.db.tenants.find_one({"_id": state["tenant_id"]})
    if tenant:
        state["system_prompt"] = tenant.get("system_prompt", "")
        state["media_library"] = tenant.get("media_library", {})
    else:
        state["system_prompt"] = "You are a helpful assistant."
        state["media_library"] = {}
        
    # 2. Fetch last 5 messages from chat history
    session_id = state["session_id"]
    cursor = db_manager.db.messages.find({"session_id": session_id})
    cursor.sort("timestamp", -1).limit(5)
    messages = await cursor.to_list(length=5)
    
    # Sort messages chronologically
    messages.reverse()
    
    # Form chat history list
    chat_history = []
    for msg in messages:
        chat_history.append({
            "direction": msg.get("direction"),
            "content": msg.get("content"),
            "type": msg.get("type", "text"),
            "media_url": msg.get("media_url"),
            "filename": msg.get("filename")
        })
        
    state["chat_history"] = chat_history
    return state

async def run_simulated_llm(state: AgentState) -> Dict[str, Any]:
    """Fallback Rule-Based Agent when no LLM APIs are active."""
    inbound_content = state["inbound_message"].get("content", "").lower()
    tenant_id = state["tenant_id"]
    media_library = state["media_library"]
    
    # 1. Sentiment Score logic (look for frustrating keywords)
    angry_keywords = ["bad", "terrible", "horrible", "scam", "human", "worst", "hate", "refund", "manager", "support"]
    sentiment_score = 3.0
    for keyword in angry_keywords:
        if keyword in inbound_content:
            sentiment_score = 1.0
            break

    # 2. Key matching and synonym mapping for Media items
    selected_media_key = None
    selected_media_item = None
    
    # Define synonyms for each tenant's media keys to ensure robust matching
    synonyms = {}
    if tenant_id == "tenant_a":
        synonyms = {
            "catalog": ["catalog", "pdf", "document", "doc", "brochure", "booklet", "list"],
            "sofa": ["sofa", "image", "photo", "picture", "showroom", "couch"]
        }
    else:  # tenant_b
        synonyms = {
            "invoice": ["invoice", "pdf", "document", "doc", "sheet", "bill", "receipt"],
            "diagram": ["diagram", "image", "photo", "picture", "engine", "schematic"]
        }
        
    for key, item in media_library.items():
        match_words = synonyms.get(key, [key])
        if any(word in inbound_content for word in match_words):
            selected_media_key = key
            selected_media_item = item
            break
            
    # 3. Formulate response body based on matching common questions
    if sentiment_score < 2.0:
        reply_content = "I understand you're frustrated. I am transferring you to a human manager right away. They will review this conversation and assist you."
        reply_type = "text"
    elif selected_media_key:
        reply_type = selected_media_item.get("type", "text")
        if tenant_id == "tenant_a":
            if selected_media_key == "catalog":
                reply_content = "Certainly! Here is our latest *Luxury Furniture Catalog* showing our premium collection. Let me know if you like any showroom items!"
            else:
                reply_content = "Here is the showroom image of our *premium sofa set*. It features high-durability fabrics and a sleek contemporary design. Do you have any questions about custom pricing?"
        else:  # tenant_b (automotive)
            if selected_media_key == "invoice":
                reply_content = "Sure thing! Attached is your *sample invoice* detailing the diagnostic services. Please review it and verify your appointment time."
            else:
                reply_content = "I have fetched the *engine repair diagram* for your reference. This highlights the cylinder layout we discussed."
    elif "price" in inbound_content or "cost" in inbound_content or "how much" in inbound_content:
        reply_type = "text"
        if tenant_id == "tenant_a":
            reply_content = "Our handcrafted luxury armchairs start at *$1,200*, and sectional sofas start at *$3,500*. You can request our 'catalog' to view the complete custom pricing list!"
        else:
            reply_content = "Diagnostic inspection is *$89*, and standard labor is *$110/hour*. I can send you a sample 'invoice' sheet to see the typical breakdown."
    elif "location" in inbound_content or "address" in inbound_content or "where" in inbound_content:
        reply_type = "text"
        if tenant_id == "tenant_a":
            reply_content = "Our premium showroom is located at *450 Luxury Plaza, Suite A, New York, NY*. Stop by to feel the premium upholstery!"
        else:
            reply_content = "Our repair shop is located at *120 Auto Drive, Houston, TX*. You can ask for our 'diagram' if you want a look at our workshop layout."
    elif "hours" in inbound_content or "open" in inbound_content or "time" in inbound_content:
        reply_type = "text"
        reply_content = "We are open *Monday through Saturday, from 9:00 AM to 6:00 PM*. We are closed on Sundays."
    elif "appointment" in inbound_content or "book" in inbound_content or "schedule" in inbound_content:
        reply_type = "text"
        if tenant_id == "tenant_a":
            reply_content = "I would be happy to schedule a private showroom consultation for you. What day and time work best?"
        else:
            reply_content = "Let's get your service scheduled. What day are you looking to bring your car in, and what is your vehicle model?"
    elif any(greet in inbound_content for greet in ["hello", "hi", "hey", "hola"]):
        reply_type = "text"
        if tenant_id == "tenant_a":
            reply_content = "Hello! Welcome to the *Luxury Furniture Store*. How can I help you design your home today? You can ask for our 'catalog' or details on our 'sofa' design!"
        else:
            reply_content = "Hi there! Welcome to *Automotive Care*. How can I assist you with your vehicle today? Feel free to ask about your service 'invoice' or 'diagram'!"
    else:
        reply_type = "text"
        if tenant_id == "tenant_a":
            reply_content = "Thank you for reaching out to the *Luxury Furniture Store*. I'd love to help you find the perfect piece. Feel free to ask about our 'catalog' or 'sofa' features, or ask about our showroom location!"
        else:
            reply_content = "Thank you for contacting *Automotive Care*. I can assist you with quotes, booking, or repairs. Feel free to ask for a sample 'invoice', 'diagram' details, or our pricing!"

    return {
        "reply_type": reply_type,
        "reply_content": reply_content,
        "media_key": selected_media_key,
        "sentiment_score": sentiment_score
    }

async def run_real_llm(state: AgentState) -> Dict[str, Any]:
    """Queries OpenAI or Google Gemini LLM with structured output prompt."""
    inbound_content = state["inbound_message"].get("content", "")
    tenant_id = state["tenant_id"]
    media_library = state["media_library"]
    system_prompt = state["system_prompt"]
    chat_history = state["chat_history"]

    # Format chat history for prompt
    history_str = ""
    for msg in chat_history:
        role = "Assistant" if msg["direction"] == "outbound" else "User"
        media_info = f" (Media Attachment: {msg['filename']})" if msg.get("filename") else ""
        history_str += f"{role}: {msg['content']}{media_info}\n"

    # Format media library instructions
    media_lib_str = json.dumps(media_library, indent=2)
    media_keys = list(media_library.keys())
    keys_str = " | ".join(['"' + k + '"' for k in media_keys]) if media_keys else ""
    keys_list_str = ", ".join(['"' + k + '"' for k in media_keys])
    media_key_instruction = f"""matching the keys ({keys_list_str}), select that media asset. 
    Map requests for any document, PDF, catalog, or brochure to the document-type asset (e.g. "catalog" or "invoice").
    Map requests for any image, photo, picture, or diagram to the image-type asset (e.g. "sofa" or "diagram").
    If they ask for or imply they want to see/receive an asset, select the matching media key. Otherwise, select null.""" if media_keys else "select null."
    media_key_schema = f"{keys_str} | null" if keys_str else "null"

    prompt = f"""
System instructions:
{system_prompt}

Available Media Library Assets:
{media_lib_str}

Conversation History:
{history_str}

Current Message:
User: {inbound_content}

Your Task:
1. Conduct sentiment analysis. Analyze if the user is extremely frustrated, angry, or explicitly demanding human assistance. Rate sentiment from 1.0 (extremely frustrated) to 5.0 (extremely satisfied). Default is 3.0.
2. Determine if the user is requesting visual/data assets matching any triggers in the Media Library.
   - If they ask for assets, {media_key_instruction}
3. Formulate the response body following the tenant's brand voice. Use markdown formatting like *bold* or _italics_ when appropriate.

Return ONLY a valid JSON object matching the following structure:
{{
  "reply_type": "text" | "image" | "document",
  "reply_content": "Your text response",
  "media_key": {media_key_schema},
  "sentiment_score": float
}}
"""

    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(openai_api_key=settings.OPENAI_API_KEY, model="gpt-4o-mini", temperature=0.0)
            response = await llm.ainvoke(prompt)
            result = json.loads(response.content.strip())
            return result
        except Exception as e:
            logger.error(f"OpenAI LLM failed: {e}. Trying Gemini fallback.")
            
    if settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(google_api_key=settings.GEMINI_API_KEY, model="gemini-2.5-flash", temperature=0.0)
            response = await llm.ainvoke(prompt)
            
            # Unpack text content if response is returned in a list of parts
            if isinstance(response.content, list):
                raw_content = ""
                for part in response.content:
                    if isinstance(part, dict) and "text" in part:
                        raw_content += part["text"]
                    elif isinstance(part, str):
                        raw_content += part
            else:
                raw_content = response.content

            raw_content = raw_content.strip()
            # Remove markdown JSON blocks if present
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            result = json.loads(raw_content.strip())
            return result
        except Exception as e:
            logger.error(f"Gemini LLM failed: {e}. Falling back to Rule-Based simulator.")

    # Rule-Based Simulator as a final fallback
    return await run_simulated_llm(state)

async def llm_reasoning_node(state: AgentState) -> AgentState:
    """Node 3: Resolves next response, does sentiment analysis & media selection."""
    state["node_trace"].append("LLM Reasoning Node")
    
    # 1. Handle Multimodal Input if the user sent an image
    inbound_msg = state["inbound_message"]
    if inbound_msg.get("type") == "image" and inbound_msg.get("media_url"):
        logger.info("Inbound image detected. Appending description to content.")
        description = "[Image Inbound: User sent an image showing items of interest. Proceed to ask how we can help with this item.]"
        # Optional: Add real multimodal parsing here using Gemini/OpenAI
        if settings.GEMINI_API_KEY or settings.OPENAI_API_KEY:
            try:
                # We can write a quick multimodal parser helper if needed
                pass
            except Exception as e:
                logger.error(f"Multimodal image parsing failed: {e}")
        inbound_msg["content"] = f"{inbound_msg.get('content', '')} {description}".strip()

    # 2. Query LLM (real or simulated)
    result = await run_real_llm(state)
    logger.info(f"LLM Reasoning result: {result}")
    
    # 3. Setup suggested reply and update session status
    reply_type = result.get("reply_type", "text")
    reply_content = result.get("reply_content", "")
    media_key = result.get("media_key")
    sentiment = result.get("sentiment_score", 3.0)
    
    media_url = None
    filename = None
    
    if media_key and media_key in state["media_library"]:
        media_item = state["media_library"][media_key]
        media_url = media_item.get("url")
        filename = media_item.get("filename")
        reply_type = media_item.get("type", "text")
        
    state["suggested_reply"] = {
        "type": reply_type,
        "content": reply_content,
        "media_url": media_url,
        "filename": filename
    }
    state["sentiment_score"] = sentiment
    
    if sentiment < 2.0:
        state["session_status"] = "NEEDS_HUMAN"
    else:
        state["session_status"] = "AGENT_RESPONDING"
        
    return state

async def dispatcher_node(state: AgentState) -> AgentState:
    """Node 4: Sends WhatsApp payload, saves outbound response, turns off typing indicator."""
    state["node_trace"].append("Dispatcher Node")
    customer_phone = state["customer_phone"]
    reply = state["suggested_reply"]
    session_id = state["session_id"]
    
    outbound_msg_id = f"out_msg_{datetime.now(timezone.utc).timestamp()}"
    
    # 1. Dispatch payload via WhatsApp Graph API
    try:
        if reply["type"] == "image" and reply["media_url"]:
            await whatsapp_client.send_image_message(customer_phone, reply["media_url"], reply["content"])
        elif reply["type"] == "document" and reply["media_url"]:
            await whatsapp_client.send_document_message(customer_phone, reply["media_url"], reply["filename"], reply["content"])
        else:
            await whatsapp_client.send_text_message(customer_phone, reply["content"])
    except Exception as e:
        logger.error(f"Failed to dispatch message to customer: {e}")

    # 2. Turn off typing indicator (in Meta API, sending a regular message automatically
    # extinguishes the typing state, but we can also fire a clean stop to be thorough)
    try:
        await whatsapp_client.toggle_typing_indicator(customer_phone, is_active=False)
    except Exception as e:
        logger.error(f"Failed to clear typing indicator: {e}")

    # 3. Log outbound message to database
    await db_manager.db.messages.insert_one({
        "_id": outbound_msg_id,
        "session_id": session_id,
        "tenant_id": state["tenant_id"],
        "customer_phone": customer_phone,
        "direction": "outbound",
        "type": reply["type"],
        "content": reply["content"],
        "media_url": reply["media_url"],
        "filename": reply["filename"],
        "timestamp": datetime.now(timezone.utc)
    })

    # 4. Save session final state
    await db_manager.db.sessions.update_one(
        {"_id": session_id},
        {
            "$set": {
                "status": state["session_status"],
                "sentiment_score": state["sentiment_score"],
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return state

# ----------------- Graph Construction -----------------

def build_agent_graph():
    builder = StateGraph(AgentState)
    
    # Define Nodes
    builder.add_node("Acknowledge", acknowledge_node)
    builder.add_node("ContextRetriever", context_retriever_node)
    builder.add_node("LLMReasoning", llm_reasoning_node)
    builder.add_node("Dispatcher", dispatcher_node)
    
    # Define Edges (Strict Linear Flow)
    builder.set_entry_point("Acknowledge")
    builder.add_edge("Acknowledge", "ContextRetriever")
    builder.add_edge("ContextRetriever", "LLMReasoning")
    builder.add_edge("LLMReasoning", "Dispatcher")
    builder.add_edge("Dispatcher", END)
    
    return builder.compile()

agent_graph = build_agent_graph()
