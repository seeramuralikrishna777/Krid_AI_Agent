import React, { useState, useEffect, useRef } from 'react';
import './App.css';

// Interfaces matching backend schemas
interface MediaItem {
  url: string;
  type: string;
  filename?: string;
}

interface Tenant {
  _id: string;
  name: string;
  system_prompt: string;
  media_library: Record<string, MediaItem>;
}

interface ChatSession {
  _id: string;
  customer_phone: string;
  tenant_id: string;
  status: string;
  sentiment_score: number;
  context_variables: {
    last_trace?: string[];
    last_reply?: {
      type: string;
      content: string;
      media_url?: string;
      filename?: string;
    };
    [key: string]: any;
  };
  updated_at: string;
}

interface MessageLog {
  _id?: string;
  session_id: string;
  tenant_id: string;
  customer_phone: string;
  direction: 'inbound' | 'outbound';
  type: 'text' | 'image' | 'document';
  content: string;
  media_url?: string;
  mime_type?: string;
  filename?: string;
  timestamp: string;
}

// Inline SVGs for zero-dependency icons
const Icons = {
  Chat: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    </svg>
  ),
  Send: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="22" y1="2" x2="11" y2="13"></line>
      <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
    </svg>
  ),
  Document: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
      <polyline points="14 2 14 8 20 8"></polyline>
      <line x1="16" y1="13" x2="8" y2="13"></line>
      <line x1="16" y1="17" x2="8" y2="17"></line>
      <polyline points="10 9 9 9 8 9"></polyline>
    </svg>
  ),
  Image: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
      <circle cx="8.5" cy="8.5" r="1.5"></circle>
      <polyline points="21 15 16 10 5 21"></polyline>
    </svg>
  ),
  Download: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
      <polyline points="7 10 12 15 17 10"></polyline>
      <line x1="12" y1="15" x2="12" y2="3"></line>
    </svg>
  ),
  Speaker: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect>
      <circle cx="12" cy="14" r="4"></circle>
      <line x1="12" y1="6" x2="12.01" y2="6"></line>
    </svg>
  ),
  User: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
      <circle cx="12" cy="7" r="4"></circle>
    </svg>
  ),
  Search: () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"></circle>
      <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
    </svg>
  )
};

export default function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>('tenant_a');
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [newChatPhone, setNewChatPhone] = useState<string>('');
  const [emptyChatPhone, setEmptyChatPhone] = useState<string>('');
  
  // Dashboard Tabs & Drawers
  const [activeDiagTab, setActiveDiagTab] = useState<'trace' | 'db' | 'payload'>('trace');
  const [isBroadcastOpen, setIsBroadcastOpen] = useState<boolean>(false);
  
  // Simulated message state
  const [simMsgType, setSimMsgType] = useState<'text' | 'image' | 'document'>('text');
  const [simTextContent, setSimTextContent] = useState<string>('');
  const [simMediaUrl, setSimMediaUrl] = useState<string>('');
  const [simFilename, setSimFilename] = useState<string>('');
  
  // Broadcast template state
  const [broadcastNumbers, setBroadcastNumbers] = useState<string>('');
  const [broadcastTemplate, setBroadcastTemplate] = useState<string>('new_catalog_promo');
  const [broadcastMessage, setBroadcastMessage] = useState<string>('');

  const chatEndRef = useRef<HTMLDivElement>(null);
  const API_BASE = window.location.origin.includes('5173') ? 'http://localhost:8000' : '';

  // 1. Initial Load: Tenants list
  useEffect(() => {
    fetch(`${API_BASE}/api/tenants`)
      .then(res => res.json())
      .then(data => {
        setTenants(data);
        if (data.length > 0) {
          setSelectedTenantId(data[0]._id);
        }
      })
      .catch(err => console.error("Error fetching tenants:", err));
  }, []);

  // 2. Load Active Sessions for selected Tenant (Polled)
  useEffect(() => {
    const fetchSessions = () => {
      fetch(`${API_BASE}/api/sessions?tenant_id=${selectedTenantId}`)
        .then(res => res.json())
        .then(data => {
          // If selectedSession exists but is not in the database sessions list yet, prepend it to the list
          let updatedSessions = data;
          if (selectedSession && !data.some((s: ChatSession) => s._id === selectedSession._id)) {
            updatedSessions = [selectedSession, ...data];
          }
          setSessions(updatedSessions);
          
          // Re-sync selected session details if already selected
          if (selectedSession) {
            const updated = data.find((s: ChatSession) => s._id === selectedSession._id);
            if (updated) {
              setSelectedSession(updated);
            }
          }
        })
        .catch(err => console.error("Error fetching sessions:", err));
    };

    fetchSessions();
    const interval = setInterval(fetchSessions, 2000);
    return () => clearInterval(interval);
  }, [selectedTenantId, selectedSession?._id]);

  // 3. Load Message logs for selected session (Polled)
  useEffect(() => {
    if (!selectedSession) {
      setMessages([]);
      return;
    }

    const fetchMessages = () => {
      fetch(`${API_BASE}/api/messages?session_id=${selectedSession._id}`)
        .then(res => res.json())
        .then(data => {
          setMessages(data);
        })
        .catch(err => console.error("Error fetching messages:", err));
    };

    fetchMessages();
    const interval = setInterval(fetchMessages, 2000);
    return () => clearInterval(interval);
  }, [selectedSession?._id]);

  // 4. Auto scroll chat window
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, selectedSession?.status]);

  // Handle media defaults in simulator when switching media type
  useEffect(() => {
    const activeTenant = tenants.find(t => t._id === selectedTenantId);
    if (!activeTenant) return;

    const mediaKeys = Object.keys(activeTenant.media_library || {});

    if (simMsgType === 'image') {
      const imgKey = mediaKeys.find(k => activeTenant.media_library[k].type === 'image') || 'sofa';
      const imgItem = activeTenant.media_library[imgKey];
      const imgUrl = imgItem?.url || "https://images.unsplash.com/photo-1555041469-a586c61ea9bc";
      const imgName = imgItem?.filename || "showroom_sofa.jpg";
      setSimMediaUrl(imgUrl);
      setSimFilename(imgName);
    } else if (simMsgType === 'document') {
      const docKey = mediaKeys.find(k => activeTenant.media_library[k].type === 'document') || 'catalog';
      const docItem = activeTenant.media_library[docKey];
      const docUrl = docItem?.url || "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf";
      const docName = docItem?.filename || "catalog.pdf";
      setSimMediaUrl(docUrl);
      setSimFilename(docName);
    } else {
      setSimMediaUrl('');
      setSimFilename('');
    }
  }, [simMsgType, selectedTenantId, tenants]);

  // Send simulated user webhook
  const handleSendSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!simTextContent.trim() && simMsgType === 'text') return;

    const phone = selectedSession ? selectedSession.customer_phone : "1234567890";
    
    const payload = {
      tenant_id: selectedTenantId,
      customer_phone: phone,
      content: simMsgType === 'text' ? simTextContent : `[Simulator: Sent ${simMsgType}]`,
      type: simMsgType,
      media_url: simMsgType !== 'text' ? simMediaUrl : undefined,
      filename: simMsgType !== 'text' ? simFilename : undefined,
      mime_type: simMsgType === 'image' ? 'image/jpeg' : simMsgType === 'document' ? 'application/pdf' : undefined
    };

    try {
      await fetch(`${API_BASE}/api/simulate/incoming`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      // If we don't have an active session, mock select the newly created one
      if (!selectedSession) {
        setSelectedSession({
          _id: `${selectedTenantId}_${phone}`,
          customer_phone: phone,
          tenant_id: selectedTenantId,
          status: 'WAITING_FOR_BOT',
          sentiment_score: 3.0,
          context_variables: {},
          updated_at: new Date().toISOString()
        });
      }
      
      // Clear inputs
      setSimTextContent('');
    } catch (err) {
      console.error("Failed to send simulation payload:", err);
    }
  };

  // Dispatch Broadcast Campaign
  const handleSendBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!broadcastNumbers.trim()) return;

    const numbers = broadcastNumbers
      .split(',')
      .map(n => n.trim())
      .filter(n => n.length > 0);

    const payload = {
      tenant_id: selectedTenantId,
      numbers,
      template_name: broadcastTemplate,
      custom_message: broadcastMessage ? broadcastMessage : undefined
    };

    try {
      const res = await fetch(`${API_BASE}/api/broadcast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        alert(`Successfully queued broadcast campaign to ${numbers.length} numbers.`);
        setIsBroadcastOpen(false);
        setBroadcastNumbers('');
        setBroadcastMessage('');
      } else {
        const error = await res.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (err) {
      console.error("Broadcast failed:", err);
    }
  };

  // Create/simulate a new conversation with custom phone number
  const handleCreateNewChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newChatPhone.trim()) return;
    
    const phone = newChatPhone.trim();
    const newSession: ChatSession = {
      _id: `${selectedTenantId}_${phone}`,
      customer_phone: phone,
      tenant_id: selectedTenantId,
      status: 'RESOLVED',
      sentiment_score: 3.0,
      context_variables: {},
      updated_at: new Date().toISOString()
    };
    
    // Add to sessions list locally if it doesn't exist
    if (!sessions.some(s => s._id === newSession._id)) {
      setSessions(prev => [newSession, ...prev]);
    }
    
    setSelectedSession(newSession);
    setNewChatPhone('');
  };

  const handleCreateNewChatFromEmpty = (e: React.FormEvent) => {
    e.preventDefault();
    if (!emptyChatPhone.trim()) return;
    
    const phone = emptyChatPhone.trim();
    const newSession: ChatSession = {
      _id: `${selectedTenantId}_${phone}`,
      customer_phone: phone,
      tenant_id: selectedTenantId,
      status: 'RESOLVED',
      sentiment_score: 3.0,
      context_variables: {},
      updated_at: new Date().toISOString()
    };
    
    // Add to sessions list locally if it doesn't exist
    if (!sessions.some(s => s._id === newSession._id)) {
      setSessions(prev => [newSession, ...prev]);
    }
    
    setSelectedSession(newSession);
    setEmptyChatPhone('');
  };

  // Filter sessions based on search
  const filteredSessions = sessions.filter(s => 
    s.customer_phone.includes(searchQuery)
  );

  const activeTenantObj = tenants.find(t => t._id === selectedTenantId);
  const isTyping = selectedSession?.status === 'WAITING_FOR_BOT';
  
  // Extract trace lists for visualizer
  const currentTrace = selectedSession?.context_variables?.last_trace || [];
  
  // Pre-seed simulator messages for helper testing click
  const preSeedInput = (txt: string) => {
    setSimMsgType('text');
    setSimTextContent(txt);
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header glass-panel">
        <div className="logo-section">
          <h1>
            <span style={{ color: 'var(--primary)', display: 'inline-flex' }}><Icons.Chat /></span>
            Krid.AI WhatsApp Orchestrator
          </h1>
        </div>
        <div className="header-controls">
          <div className="system-mode-badge">
            <span className={`mode-dot success`}></span>
            <span>Local Sandbox Mode (Zero-Config Enabled)</span>
          </div>
          <button className="btn btn-secondary" onClick={() => setIsBroadcastOpen(true)}>
            <Icons.Speaker /> Broadcast Campaign
          </button>
        </div>
      </header>

      {/* Tenant Switcher */}
      <section className="tenant-tabs">
        {tenants.map(t => (
          <button
            key={t._id}
            className={`tenant-tab ${selectedTenantId === t._id ? 'active' : ''}`}
            onClick={() => {
              setSelectedTenantId(t._id);
              setSelectedSession(null);
            }}
          >
            {t.name}
            <div style={{ fontSize: '0.7rem', opacity: 0.7, fontWeight: 400 }}>
              ID: {t._id}
            </div>
          </button>
        ))}
      </section>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Column 1: Active Chat Sessions */}
        <div className="sessions-panel glass-panel">
          <div className="panel-title">
            <span>Conversations</span>
            <span className="badge badge-info">{filteredSessions.length} Active</span>
          </div>
          <div className="search-container">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <input
                  type="text"
                  className="search-input"
                  placeholder="Search phone number..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                />
              </div>
              <form onSubmit={handleCreateNewChat} style={{ display: 'flex', gap: '6px' }}>
                <input
                  type="text"
                  className="search-input"
                  style={{ flex: 1, fontSize: '0.8rem', padding: '6px 10px' }}
                  placeholder="New phone (e.g. 12345)..."
                  value={newChatPhone}
                  onChange={e => setNewChatPhone(e.target.value.replace(/\D/g, ''))}
                />
                <button type="submit" className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '0.75rem', height: 'auto', minHeight: 'unset', flexShrink: 0 }}>
                  + Add
                </button>
              </form>
            </div>
          </div>
          
          <div className="sessions-list">
            {filteredSessions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px 10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                No active chat sessions. Send a message to start.
              </div>
            ) : (
              filteredSessions.map(session => {
                const isSelected = selectedSession?._id === session._id;
                const isNeedsHuman = session.status === 'NEEDS_HUMAN';
                const formattedTime = new Date(session.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                
                return (
                  <div
                    key={session._id}
                    className={`session-item ${isSelected ? 'selected' : ''} ${isNeedsHuman ? 'needs-human' : ''}`}
                    onClick={() => setSelectedSession(session)}
                  >
                    <div className="session-item-header">
                      <span className="customer-num">+{session.customer_phone}</span>
                      <span className="session-time">{formattedTime}</span>
                    </div>
                    <div className="session-details">
                      {isNeedsHuman ? (
                        <span className="badge badge-danger">Needs Human</span>
                      ) : session.status === 'WAITING_FOR_BOT' ? (
                        <span className="badge badge-warning">Thinking...</span>
                      ) : (
                        <span className="badge badge-success">Active</span>
                      )}
                      
                      <span className="sentiment-dot">
                        Score: {session.sentiment_score.toFixed(1)}/5.0
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Column 2: Chat Screen & Webhook Simulator */}
        <div className="chat-panel glass-panel">
          {selectedSession ? (
            <>
              {/* Chat Header */}
              <div className="chat-header">
                <div className="chat-user-info">
                  <h3>+{selectedSession.customer_phone}</h3>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Session: {selectedSession._id}
                  </div>
                </div>
                <div>
                  <span className={`badge ${selectedSession.status === 'NEEDS_HUMAN' ? 'badge-danger' : 'badge-success'}`}>
                    {selectedSession.status}
                  </span>
                </div>
              </div>

              {/* Chat History */}
              <div className="chat-history-container">
                {selectedSession.status === 'NEEDS_HUMAN' && (
                  <div className="handover-banner fade-in">
                    <span>⚠️</span>
                    <div>
                      <strong>Fallback Handover Triggered.</strong> Automated replies are halted due to high customer frustration (sentiment score: {selectedSession.sentiment_score.toFixed(1)}/5.0).
                    </div>
                  </div>
                )}

                {messages.length === 0 ? (
                  <div className="empty-chat">
                    <Icons.Chat />
                    <p>Start the conversation using the sandbox simulator below.</p>
                  </div>
                ) : (
                  messages.map((msg, index) => {
                    const getLocalTime = (ts: string) => {
                      if (!ts) return '';
                      let clean = ts;
                      if (!clean.endsWith('Z') && !clean.match(/[+-]\d{2}:?\d{2}$/)) {
                        clean += 'Z';
                      }
                      return new Date(clean).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    };
                    const isInbound = msg.direction === 'inbound';
                    const time = getLocalTime(msg.timestamp);
                    
                    return (
                      <div
                        key={msg._id || index}
                        className={`message-bubble-wrapper ${isInbound ? 'inbound' : 'outbound'} fade-in`}
                      >
                        <div className="message-bubble">
                          {msg.type === 'image' && msg.media_url && (
                            <img src={msg.media_url} alt="Showroom" className="bubble-image" />
                          )}
                          
                          {msg.type === 'document' && msg.media_url && (
                            <a href={msg.media_url} target="_blank" rel="noreferrer" className="bubble-doc">
                              <Icons.Document />
                              <div style={{ textAlign: 'left' }}>
                                <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>{msg.filename || 'Document'}</div>
                                <div style={{ fontSize: '0.65rem', opacity: 0.7 }}>Click to view catalog (PDF)</div>
                              </div>
                              <div style={{ marginLeft: 'auto' }}><Icons.Download /></div>
                            </a>
                          )}
                          
                          <div style={{ whiteSpace: 'pre-wrap' }}>
                            {msg.content}
                          </div>
                        </div>
                        <span className="message-meta" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          {isInbound ? 'Customer' : 'Bot'} • {time}
                          {!isInbound && <span style={{ color: '#38bdf8', fontSize: '0.9rem', fontWeight: 'bold', lineHeight: 1 }}>✓✓</span>}
                          {isInbound && <span style={{ color: '#34d399', fontSize: '0.7rem', fontWeight: 600, marginLeft: '2px' }}>• Read</span>}
                        </span>
                      </div>
                    );
                  })
                )}

                {/* Simulated typing indicator */}
                {isTyping && (
                  <div className="message-bubble-wrapper outbound fade-in">
                    <div className="message-bubble" style={{ background: '#ffffff', padding: '10px 16px', borderTopLeftRadius: '0px' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        Bot typing 
                        <span style={{ display: 'inline-flex', gap: '3px' }}>
                          <span className="typing-dot"></span>
                          <span className="typing-dot"></span>
                          <span className="typing-dot"></span>
                        </span>
                      </span>
                    </div>
                  </div>
                )}
                
                <div ref={chatEndRef} />
              </div>

              {/* Webhook Sandbox Simulator */}
              <div className="simulator-footer">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)' }}>
                    📲 WHATSAPP WEBHOOK SIMULATOR
                  </span>
                  {simMsgType === 'text' && (
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button className="badge badge-info" style={{ cursor: 'pointer' }} onClick={() => preSeedInput("Hello")}>Hi</button>
                      <button className="badge badge-info" style={{ cursor: 'pointer' }} onClick={() => preSeedInput(selectedTenantId === 'tenant_a' ? "Can I see your product catalog?" : "Can you send the invoice sheet?")}>Catalog request</button>
                      <button className="badge badge-info" style={{ cursor: 'pointer' }} onClick={() => preSeedInput(selectedTenantId === 'tenant_a' ? "I want to buy a sofa" : "Show me the repair diagram")}>Media request</button>
                      <button className="badge badge-danger" style={{ cursor: 'pointer' }} onClick={() => preSeedInput("This is terrible support, transfer me to a manager right now!")}>Angry</button>
                    </div>
                  )}
                </div>
                
                <form onSubmit={handleSendSimulation} className="sim-row">
                  <select
                    className="sim-select"
                    value={simMsgType}
                    onChange={e => setSimMsgType(e.target.value as any)}
                  >
                    <option value="text">Text Message</option>
                    <option value="image">Send Image URL</option>
                    <option value="document">Send Document PDF</option>
                  </select>

                  {simMsgType === 'text' ? (
                    <input
                      type="text"
                      className="sim-input"
                      placeholder="Type simulated message to webhook..."
                      value={simTextContent}
                      onChange={e => setSimTextContent(e.target.value)}
                    />
                  ) : (
                    <div style={{ flex: 1, display: 'flex', gap: '8px' }}>
                      <input
                        type="text"
                        className="sim-input"
                        placeholder="Public Attachment URL..."
                        value={simMediaUrl}
                        onChange={e => setSimMediaUrl(e.target.value)}
                      />
                      <input
                        type="text"
                        className="sim-input"
                        style={{ maxWidth: '140px' }}
                        placeholder="filename.ext"
                        value={simFilename}
                        onChange={e => setSimFilename(e.target.value)}
                      />
                    </div>
                  )}

                  <button type="submit" className="btn" disabled={isTyping}>
                    <Icons.Send /> Trigger
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="empty-chat">
              <Icons.Chat />
              <h2>Welcome to Multi-Tenant Chat Audit Logs</h2>
              <p>Please select a conversation from the left panel to begin auditing agent execution and logs.</p>
              <div style={{ width: '100%', maxWidth: '360px', marginTop: '15px' }} className="glass-panel">
                <form onSubmit={handleCreateNewChatFromEmpty} style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)', textAlign: 'center', letterSpacing: '0.05em' }}>
                    SIMULATE A NEW CONVERSATION
                  </div>
                  <input
                    type="text"
                    className="sim-input"
                    placeholder="Enter customer phone number..."
                    value={emptyChatPhone}
                    onChange={e => setEmptyChatPhone(e.target.value.replace(/\D/g, ''))}
                  />
                  <button type="submit" className="btn" style={{ justifyContent: 'center' }}>
                    Create & Simulate Chat
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>

        {/* Column 3: Live LangGraph Pipeline & Diagnostics */}
        <div className="diag-panel glass-panel">
          <div className="diag-tabs">
            <div
              className={`diag-tab ${activeDiagTab === 'trace' ? 'active' : ''}`}
              onClick={() => setActiveDiagTab('trace')}
            >
              LangGraph State Flow
            </div>
            <div
              className={`diag-tab ${activeDiagTab === 'db' ? 'active' : ''}`}
              onClick={() => setActiveDiagTab('db')}
            >
              DB Document
            </div>
            <div
              className={`diag-tab ${activeDiagTab === 'payload' ? 'active' : ''}`}
              onClick={() => setActiveDiagTab('payload')}
            >
              Pre-seeded Catalog
            </div>
          </div>

          <div className="diag-content">
            {activeDiagTab === 'trace' && (
              <div className="trace-graph fade-in">
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Execution path of the last message processed for this session.
                </div>
                
                {/* Node 1 */}
                <div className={`trace-node ${currentTrace.includes("Acknowledge Node") || isTyping ? 'active' : ''}`}>
                  <div className="node-dot"></div>
                  <div className="node-card">
                    <div className="node-name">1. Acknowledge Node</div>
                    <div className="node-desc">Fires WhatsApp read-receipt & typing indicator. Saves inbound logs.</div>
                  </div>
                </div>

                {/* Node 2 */}
                <div className={`trace-node ${currentTrace.includes("Context Retriever Node") ? 'active' : ''}`}>
                  <div className="node-dot"></div>
                  <div className="node-card">
                    <div className="node-name">2. Context Retriever Node</div>
                    <div className="node-desc">Pulls Tenant instruction rules & last 5 conversation history.</div>
                  </div>
                </div>

                {/* Node 3 */}
                <div className={`trace-node ${currentTrace.includes("LLM Reasoning Node") ? 'active' : ''}`}>
                  <div className="node-dot"></div>
                  <div className="node-card">
                    <div className="node-name">3. LLM Reasoning Node</div>
                    <div className="node-desc">Analyzes client intent, parses sentiments, determines asset mapping.</div>
                  </div>
                </div>

                {/* Node 4 */}
                <div className={`trace-node ${currentTrace.includes("Dispatcher Node") ? 'active' : ''}`}>
                  <div className="node-dot"></div>
                  <div className="node-card">
                    <div className="node-name">4. Dispatcher Node</div>
                    <div className="node-desc">Constructs media payloader & sends message, extinguishing typing state.</div>
                  </div>
                </div>
              </div>
            )}

            {activeDiagTab === 'db' && (
              <div className="fade-in">
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Active Chat Session Record
                </div>
                {selectedSession ? (
                  <pre className="json-viewer">
                    {JSON.stringify(selectedSession, null, 2)}
                  </pre>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No session selected.</div>
                )}
              </div>
            )}

            {activeDiagTab === 'payload' && (
              <div className="fade-in">
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                  Tenant Brand Profile & Asset Catalog
                </div>
                {activeTenantObj ? (
                  <pre className="json-viewer">
                    {JSON.stringify(activeTenantObj, null, 2)}
                  </pre>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>No tenant selected.</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Broadcast Campaign Drawer Modal */}
      {isBroadcastOpen && (
        <div className="drawer-overlay" onClick={() => setIsBroadcastOpen(false)}>
          <div className="drawer" onClick={e => e.stopPropagation()}>
            <div className="drawer-header">
              <h3>Launch Template Broadcast</h3>
              <button
                className="btn btn-secondary"
                style={{ padding: '4px 8px', borderRadius: '50%' }}
                onClick={() => setIsBroadcastOpen(false)}
              >
                ✕
              </button>
            </div>
            
            <form onSubmit={handleSendBroadcast} className="drawer-body">
              <div className="form-group">
                <label className="form-label">Active Tenant</label>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'white' }}>
                  {activeTenantObj?.name || selectedTenantId}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Recipient Phone Numbers</label>
                <input
                  type="text"
                  required
                  className="form-input"
                  placeholder="e.g. 1234567890, 9876543210"
                  value={broadcastNumbers}
                  onChange={e => setBroadcastNumbers(e.target.value)}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Comma-separated phone numbers (without '+' or leading '0').
                </span>
              </div>

              <div className="form-group">
                <label className="form-label">Template Campaign</label>
                <select
                  className="form-input"
                  value={broadcastTemplate}
                  onChange={e => setBroadcastTemplate(e.target.value)}
                >
                  <option value="new_catalog_promo">New Catalog Promo (Sends Catalog PDF)</option>
                  <option value="service_reminder">Service Reminder (Sends Repair Invoice)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Custom Message (Optional)</label>
                <textarea
                  className="form-input form-textarea"
                  placeholder="Enter a message to override the template text..."
                  value={broadcastMessage}
                  onChange={e => setBroadcastMessage(e.target.value)}
                />
              </div>

              <div className="drawer-footer">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setIsBroadcastOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn">
                  <Icons.Speaker /> Dispatch Broadcast
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
