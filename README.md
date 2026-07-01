# Krid.AI Take-Home Assignment: Multi-Tenant Agentic WhatsApp Orchestrator

An end-to-end cloud-native system for a **Multi-Tenant WhatsApp AI Support & Sales Agent SaaS**. Built using **FastAPI**, **LangGraph**, **React (Vite + TypeScript)**, and **MongoDB**. 

This system features a **Dual-Mode Architecture** designed for seamless grading and deployment. It runs out-of-the-box in **Local Sandbox Mode** with zero external dependencies (using an in-memory database and WhatsApp simulator), and scales to **Production Mode** by adding environment variables (for MongoDB Atlas, Meta's WhatsApp Cloud API, and OpenAI/Gemini LLMs).

---

## 🌟 Key Features

1. **Agentic Orchestration with LangGraph**: Models message processing as a stateful graph (`Acknowledge` -> `Context Retriever` -> `LLM Reasoning` -> `Dispatcher`).
2. **Multi-Tenancy Support**:
   - **Tenant A (Luxury Furniture Store)**: Sells luxury handcrafted items. Automatically serves PDF product catalogs and sofa showroom images.
   - **Tenant B (Automotive Care)**: Schedules appointments and serves repair diagrams (JPG) and service invoice sheets (PDF).
3. **Typing Indicators & Read Receipts**: Integrates native WhatsApp typing indicator toggles and read receipts during LLM execution to prevent customer drop-off.
4. **Async Webhook Retries Prevention**: FastAPI serves inbound webhooks instantly (within 3 seconds) and hands off the LangGraph execution block to an asynchronous background worker.
5. **Built-in Webhook Simulator**: An interactive simulator directly inside the dashboard lets you mock user messages (text, images, PDFs) to verify LangGraph execution, state logs, and trace flows in real time.
6. **Sentiment-Based Human Handover**: If a customer displays frustration, the LLM sets the session state to `NEEDS_HUMAN` and halts auto-responses, highlighting the chat in red on the admin dashboard.
7. **Unified Docker Deployment**: A multi-stage Docker build bundles the compiled React frontend into the FastAPI python backend, serving the entire application on a single container port.

---

## 🏗️ Architecture & LangGraph Flow

### State Schema (`AgentState`)
```python
class AgentState(TypedDict):
    tenant_id: str
    customer_phone: str
    session_id: str
    inbound_message: dict
    chat_history: List[dict]
    system_prompt: str
    media_library: dict
    suggested_reply: dict # { type, content, media_url, filename }
    session_status: str
    sentiment_score: float
    node_trace: List[str]
```

### Graph Nodes & State Flow
```
[Inbound Webhook Payload]
         │
         ▼
┌─────────────────────────┐
│   Acknowledge Node      │ ──► Sends read receipt & toggles typing indicator ON.
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Context Retriever Node  │ ──► Retrieves active Tenant brand rules and last 5 chat logs.
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│   LLM Reasoning Node    │ ──► Performs Sentiment Analysis & decides reply/media trigger.
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│    Dispatcher Node      │ ──► Sends WhatsApp message (Text/PDF/Image) & turns typing indicator OFF.
└─────────────────────────┘
         │
         ▼
      [Done]
```

---

## ⚡ Quick-Start (Local Sandbox Mode)

You can run this application locally with **zero configurations or external accounts**.

### Prerequisites
- Node.js (v18+)
- Python (v3.9+)

### 1. Build the Frontend
Scaffold and compile the Vite + React client:
```bash
cd frontend
npm install
npm run build
cd ..
```

### 2. Setup the Python Virtual Environment & Run
Start the FastAPI server:
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open the Dashboard
Open your browser and navigate to **`http://localhost:8000`**.
*   Select **Tenant A** or **Tenant B** using the switcher.
*   Type a query in the **Webhook Simulator Panel** (e.g. *"Can I see your catalog?"*) and click **Trigger**.
*   Watch the LangGraph node trace highlight and the bot reply with media in real time!

---

## ⚙️ Production Configurations (`.env`)

To connect to production services, create a `.env` file in the `backend/` directory or set environment variables in your hosting provider:

```env
# --- SERVER ---
HOST=0.0.0.0
PORT=8000

# --- DATABASE ---
# If left empty, the application uses a mock in-memory database
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/
DB_NAME=whatsapp_agent

# --- AI PROVIDERS ---
# If both are empty, the agent runs in Simulated Rule-Based Mode
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIzaSy...

# --- META WHATSAPP BUSINESS API ---
# If empty, the system runs in Simulation Webhook Sandbox mode
WHATSAPP_TOKEN=EAAG...
WHATSAPP_PHONE_NUMBER_ID=123456789...
WEBHOOK_VERIFY_TOKEN=krid_ai_challenge_token_2026

# Secure Webhook Signature Validation (Optional)
# WEBHOOK_APP_SECRET=your_meta_app_secret
```

---

## 🐳 Cloud Deployment (GCP Cloud Run / Render)

The repository contains a production-ready multi-stage `Dockerfile`.

### Build & Run Container Locally
To build and test the single unified container locally:
```bash
docker build -t whatsapp-orchestrator .
docker run -p 8000:8000 --env-file backend/.env whatsapp-orchestrator
```

### Deploy to GCP Cloud Run
Ensure you have the Google Cloud SDK configured, then deploy with a single command:
```bash
gcloud run deploy whatsapp-orchestrator \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --port 8000
```

Once deployed, copy the secure HTTPS service URL and configure Meta's Webhook callback endpoint to:
`https://<your-cloudrun-url>/api/webhooks/whatsapp`

---

## 🧪 Verification Walkthrough

Follow these steps on the live dashboard:

1. **Verify Brand Switching**: Toggle between **Tenant A (Luxury Furniture)** and **Tenant B (Automotive Care)**. Notice the pre-seeded brand catalog schemas update in the right-side panel.
2. **Verify Media Library Routing**:
   *   For **Tenant A**, input: *"Show me a showroom sofa and your catalog."*. The bot returns the sofa image and the furniture catalog PDF.
   *   For **Tenant B**, input: *"What diagnostic details do you have? Send me an engine diagram."*. The bot replies with the engine JPG diagram.
3. **Verify Latency Indicator**: Observe the "Bot typing..." state bubble and the active highlighting of the Acknowledge and Context nodes in the "LangGraph State Flow" visualizer during processing.
4. **Verify Sentiment Handover**:
   *   Input: *"This is horrible service! Connect me to a human."*.
   *   Notice that the conversation gets flagged as `NEEDS_HUMAN`, further automated replies are blocked, and the conversation bubble turns red in the active chat list.
5. **Verify Template Broadcasts**: Click the **Broadcast Campaign** button. Put in target numbers, select a template campaign, and click **Dispatch**. You can review the logged outbound messages inside the database panel.
