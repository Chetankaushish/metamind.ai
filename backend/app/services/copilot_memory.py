import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class UserPreferences(BaseModel):
    target_roas: float = 2.5
    max_cpa_threshold: float = 25.0
    default_date_range: str = "last_30_days"
    currency: str = "USD"
    notify_on_scale: bool = True

class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Optional[Dict[str, Any]] = None

class CopilotMemoryStore:
    """
    In-memory / Redis backed session store for AI Copilot conversations,
    preferences, recent campaign views, and pinned campaigns.
    """
    def __init__(self):
        self._conversations: Dict[str, List[ConversationMessage]] = {}
        self._preferences: Dict[str, UserPreferences] = {}
        self._recent_campaigns: Dict[str, List[Dict[str, Any]]] = {}
        self._pinned_campaigns: Dict[str, List[Dict[str, Any]]] = {}

    def _key(self, user_id: str, org_id: str = "org_default") -> str:
        return f"{org_id}:{user_id}"

    def get_history(self, user_id: str, org_id: str = "org_default", limit: int = 20) -> List[ConversationMessage]:
        key = self._key(user_id, org_id)
        return self._conversations.get(key, [])[-limit:]

    def add_message(self, user_id: str, role: str, content: str, org_id: str = "org_default", metadata: Optional[Dict[str, Any]] = None):
        key = self._key(user_id, org_id)
        if key not in self._conversations:
            self._conversations[key] = []
        msg = ConversationMessage(role=role, content=content, metadata=metadata)
        self._conversations[key].append(msg)
        # Cap history length
        if len(self._conversations[key]) > 100:
            self._conversations[key] = self._conversations[key][-100:]

    def clear_history(self, user_id: str, org_id: str = "org_default"):
        key = self._key(user_id, org_id)
        self._conversations[key] = []

    def get_preferences(self, user_id: str, org_id: str = "org_default") -> UserPreferences:
        key = self._key(user_id, org_id)
        if key not in self._preferences:
            self._preferences[key] = UserPreferences()
        return self._preferences[key]

    def update_preferences(self, user_id: str, prefs: Dict[str, Any], org_id: str = "org_default") -> UserPreferences:
        key = self._key(user_id, org_id)
        current = self.get_preferences(user_id, org_id)
        updated_dict = current.model_dump()
        updated_dict.update({k: v for k, v in prefs.items() if v is not None})
        self._preferences[key] = UserPreferences(**updated_dict)
        return self._preferences[key]

    def record_campaign_view(self, user_id: str, campaign_id: str, campaign_name: str, org_id: str = "org_default"):
        key = self._key(user_id, org_id)
        if key not in self._recent_campaigns:
            self._recent_campaigns[key] = []
        # Filter out existing duplicates
        self._recent_campaigns[key] = [
            c for c in self._recent_campaigns[key] if c["id"] != campaign_id
        ]
        self._recent_campaigns[key].insert(0, {
            "id": campaign_id,
            "name": campaign_name,
            "timestamp": time.time()
        })
        self._recent_campaigns[key] = self._recent_campaigns[key][:10]

    def get_recent_campaigns(self, user_id: str, org_id: str = "org_default") -> List[Dict[str, Any]]:
        key = self._key(user_id, org_id)
        return self._recent_campaigns.get(key, [])

    def toggle_pin_campaign(self, user_id: str, campaign_id: str, campaign_name: str, org_id: str = "org_default") -> List[Dict[str, Any]]:
        key = self._key(user_id, org_id)
        if key not in self._pinned_campaigns:
            self._pinned_campaigns[key] = []
        
        existing = [c for c in self._pinned_campaigns[key] if c["id"] == campaign_id]
        if existing:
            self._pinned_campaigns[key] = [
                c for c in self._pinned_campaigns[key] if c["id"] != campaign_id
            ]
        else:
            self._pinned_campaigns[key].append({
                "id": campaign_id,
                "name": campaign_name,
                "pinned_at": time.time()
            })
        return self._pinned_campaigns[key]

    def get_pinned_campaigns(self, user_id: str, org_id: str = "org_default") -> List[Dict[str, Any]]:
        key = self._key(user_id, org_id)
        return self._pinned_campaigns.get(key, [])


copilot_memory = CopilotMemoryStore()
