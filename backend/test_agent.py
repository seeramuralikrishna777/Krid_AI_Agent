import asyncio
import logging
import sys
import os

# Adjust path to find app module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import db_manager
from app.agent import agent_graph, AgentState

# Setup basic log output
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

async def test_flow():
    print("=== Testing LangGraph Orchestrator Initialization ===")
    
    # 1. Initialize DB Connection in simulated mode
    await db_manager.connect()
    print("Database manager initialized successfully (Is Mock DB: {}).".format(db_manager.is_mock))
    
    # --- Test Tenant A ---
    inbound_message_a = {
        "id": "test_msg_101",
        "type": "text",
        "content": "Hello, I want to see your catalog.",
        "media_url": None,
        "filename": None,
        "timestamp": None
    }
    
    state_a = AgentState(
        tenant_id="tenant_a",
        customer_phone="9876543210",
        session_id="tenant_a_9876543210",
        inbound_message=inbound_message_a,
        chat_history=[],
        system_prompt="",
        media_library={},
        suggested_reply={},
        session_status="WAITING_FOR_BOT",
        sentiment_score=3.0,
        node_trace=[]
    )
    
    print("\n=== Executing LangGraph compiler loop for Tenant A ===")
    final_state_a = await agent_graph.ainvoke(state_a)
    print("Path Visited: ", " -> ".join(final_state_a["node_trace"]))
    print("Reply Type:   ", final_state_a["suggested_reply"].get("type"))
    print("Reply Content:", final_state_a["suggested_reply"].get("content"))
    
    # --- Test Tenant B ---
    inbound_message_b = {
        "id": "test_msg_102",
        "type": "text",
        "content": "Can you send the invoice sheet?",
        "media_url": None,
        "filename": None,
        "timestamp": None
    }
    
    state_b = AgentState(
        tenant_id="tenant_b",
        customer_phone="9876543210",
        session_id="tenant_b_9876543210",
        inbound_message=inbound_message_b,
        chat_history=[],
        system_prompt="",
        media_library={},
        suggested_reply={},
        session_status="WAITING_FOR_BOT",
        sentiment_score=3.0,
        node_trace=[]
    )
    
    print("\n=== Executing LangGraph compiler loop for Tenant B ===")
    final_state_b = await agent_graph.ainvoke(state_b)
    print("Path Visited: ", " -> ".join(final_state_b["node_trace"]))
    print("Reply Type:   ", final_state_b["suggested_reply"].get("type"))
    print("Reply Content:", final_state_b["suggested_reply"].get("content"))

    # Assertions
    assert "Acknowledge Node" in final_state_b["node_trace"]
    assert "Context Retriever Node" in final_state_b["node_trace"]
    assert "LLM Reasoning Node" in final_state_b["node_trace"]
    assert "Dispatcher Node" in final_state_b["node_trace"]
    
    print("\n[SUCCESS] Both tests passed!")

if __name__ == "__main__":
    asyncio.run(test_flow())

