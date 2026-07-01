import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # MongoDB settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    DB_NAME: str = os.getenv("DB_NAME", "whatsapp_agent")
    
    # LLM Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # WhatsApp Meta Cloud API settings
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WEBHOOK_VERIFY_TOKEN: str = os.getenv("WEBHOOK_VERIFY_TOKEN", "krid_ai_challenge_token_2026")
    WEBHOOK_APP_SECRET: str = os.getenv("WEBHOOK_APP_SECRET", "")
    
    # Server Settings
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    @property
    def is_simulated_whatsapp(self) -> bool:
        return not (bool(self.WHATSAPP_TOKEN) and bool(self.WHATSAPP_PHONE_NUMBER_ID))

    @property
    def is_simulated_db(self) -> bool:
        return not bool(self.MONGODB_URI)

    @property
    def has_llm_credentials(self) -> bool:
        return bool(self.OPENAI_API_KEY) or bool(self.GEMINI_API_KEY)

settings = Settings()
