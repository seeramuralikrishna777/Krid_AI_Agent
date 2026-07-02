import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from app.config import settings

logger = logging.getLogger("whatsapp_agent.database")

# In-Memory Database Fallback
class MockCursor:
    def __init__(self, data: List[Dict[str, Any]]):
        self._data = data
        self._index = 0

    def limit(self, n: int):
        self._data = self._data[:n]
        return self

    def sort(self, key_or_list, direction=None):
        # Basic sorting support for timestamp
        if isinstance(key_or_list, str) and key_or_list == "timestamp":
            reverse = direction == -1
            self._data.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=reverse)
        elif isinstance(key_or_list, list) and len(key_or_list) > 0:
            key, direction = key_or_list[0]
            reverse = direction == -1
            self._data.sort(key=lambda x: x.get(key, datetime.min), reverse=reverse)
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        if length is not None:
            return self._data[:length]
        return self._data

class MockCollection:
    def __init__(self, name: str):
        self.name = name
        self._data: Dict[str, Dict[str, Any]] = {}

    async def find_one(self, filter: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for doc in self._data.values():
            match = True
            for k, v in filter.items():
                if k == "_id" and isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                # Return copy to avoid mutation
                return dict(doc)
        return None

    def find(self, filter: Dict[str, Any] = None) -> MockCursor:
        filter = filter or {}
        matched = []
        for doc in self._data.values():
            match = True
            for k, v in filter.items():
                if k == "_id" and isinstance(v, dict) and "$in" in v:
                    if doc.get(k) not in v["$in"]:
                        match = False
                        break
                elif doc.get(k) != v:
                    match = False
                    break
            if match:
                matched.append(dict(doc))
        return MockCursor(matched)

    async def insert_one(self, document: Dict[str, Any]) -> Any:
        doc = dict(document)
        if "_id" not in doc:
            doc["_id"] = str(ObjectId())
        key = str(doc["_id"])
        self._data[key] = doc
        
        class InsertResult:
            inserted_id = key
        return InsertResult()

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any], upsert: bool = False) -> Any:
        doc = await self.find_one(filter)
        is_new = False
        if not doc:
            if upsert:
                doc = dict(filter)
                if "_id" not in doc:
                    doc["_id"] = filter.get("_id") or str(ObjectId())
                is_new = True
            else:
                class UpdateResultDummy:
                    matched_count = 0
                    modified_count = 0
                return UpdateResultDummy()

        # Apply operators
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
        if "$setOnInsert" in update and is_new:
            for k, v in update["$setOnInsert"].items():
                doc[k] = v

        self._data[str(doc["_id"])] = doc

        class UpdateResult:
            matched_count = 1
            modified_count = 1
            upserted_id = doc["_id"] if is_new else None
        return UpdateResult()

    async def delete_many(self, filter: Dict[str, Any]) -> Any:
        keys_to_delete = []
        for key, doc in self._data.items():
            match = True
            for k, v in filter.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                keys_to_delete.append(key)
        
        for k in keys_to_delete:
            del self._data[k]
            
        class DeleteResult:
            deleted_count = len(keys_to_delete)
        return DeleteResult()

class MockDatabase:
    def __init__(self):
        self._collections: Dict[str, MockCollection] = {}

    def __getattr__(self, name: str) -> MockCollection:
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

# Main Database Coordinator
class DatabaseManager:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Any = None
        self.is_mock: bool = True

    async def connect(self):
        if settings.MONGODB_URI:
            try:
                self.client = AsyncIOMotorClient(settings.MONGODB_URI)
                self.db = self.client[settings.DB_NAME]
                # Test connection
                await self.client.admin.command('ping')
                self.is_mock = False
                logger.info("Connected successfully to MongoDB.")
            except Exception as e:
                logger.error(f"MongoDB connection failed: {e}. Falling back to In-Memory DB.")
                self.db = MockDatabase()
                self.is_mock = True
        else:
            logger.info("MONGODB_URI not provided. Running in simulated database mode.")
            self.db = MockDatabase()
            self.is_mock = True
        
        await self.seed_initial_data()

    async def seed_initial_data(self):
        base_url = settings.PUBLIC_URL.rstrip("/") if settings.PUBLIC_URL else "http://127.0.0.1:8000"
        
        # Seed Tenant A
        tenant_a = {
            "_id": "tenant_a",
            "name": "Luxury Furniture Store",
            "system_prompt": "You are a professional and refined sales assistant for 'Luxury Furniture Store'. "
                             "We sell exquisite, handcrafted luxury furniture. Provide elegant, polite, and detailed answers. "
                             "Recommend catalogs or showroom images when appropriate. Always offer details about our 'sofa' (showroom image) or 'catalog' (PDF catalog) when the user expresses interest in furniture, catalogs, or sofa designs.",
            "media_library": {
                "catalog": {
                    "url": f"{base_url}/static/luxury_furniture_catalog.pdf",
                    "type": "document",
                    "filename": "luxury_furniture_catalog.pdf"
                },
                "sofa": {
                    "url": f"{base_url}/static/showroom_sofa.png",
                    "type": "image",
                    "filename": "showroom_sofa.png"
                }
            }
        }
        
        # Seed Tenant B
        tenant_b = {
            "_id": "tenant_b",
            "name": "Automotive Care",
            "system_prompt": "You are an expert, friendly service advisor for 'Automotive Care'. "
                             "We offer mechanical repair, detailing, and tuning services. "
                             "Be concise, technical, and helpful. "
                             "Offer invoice sheets or repair diagrams when the customer asks. Always offer details about our 'invoice' (sample invoice) or 'diagram' (engine diagram) when they ask about quotes, repair diagnostics, or service procedures.",
            "media_library": {
                "invoice": {
                    "url": f"{base_url}/static/sample_invoice.pdf",
                    "type": "document",
                    "filename": "sample_invoice.pdf"
                },
                "diagram": {
                    "url": f"{base_url}/static/engine_diagram.png",
                    "type": "image",
                    "filename": "engine_diagram.png"
                }
            }
        }

        # Update in-database collections
        await self.db.tenants.update_one({"_id": "tenant_a"}, {"$set": tenant_a}, upsert=True)
        await self.db.tenants.update_one({"_id": "tenant_b"}, {"$set": tenant_b}, upsert=True)
        logger.info("Tenants seeded successfully.")

db_manager = DatabaseManager()
