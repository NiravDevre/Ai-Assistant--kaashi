import os, json, traceback
from datetime import datetime
import pyrebase, config
from firebaseConfig import firebaseConfig

# Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# -------- Local Fallback (in case Firebase not available) --------
def _data_dir():
    d = os.path.join(os.getcwd(), "Data")
    os.makedirs(d, exist_ok=True)
    return d

def _mem_path():
    return os.path.join(_data_dir(), "Memory.json")

# -------- Memory Manager --------
class MemoryManager:
    def __init__(self):
        self.path = _mem_path()
        self.data = {"facts": [], "preferences": {}, "last_updated": None}
        self._load()

    # ----- Firebase Sync -----
    def _load(self):
        """Load memory from Firebase, fallback to local file."""
        try:
            if config.FirebaseUID and config.FirebaseToken:
                fb_data = db.child("users").child(config.FirebaseUID).child("memory").get(config.FirebaseToken).val()
                if fb_data:
                    self.data = fb_data
                    return
        except Exception:
            traceback.print_exc()

        # fallback local
        if os.path.exists(self.path) and os.path.getsize(self.path) > 2:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"facts": [], "preferences": {}, "last_updated": None}
                self._save()

    def _save(self):
        """Save memory to Firebase and local file."""
        self.data["last_updated"] = datetime.utcnow().isoformat()

        # save to Firebase
        try:
            if config.FirebaseUID and config.FirebaseToken:
                db.child("users").child(config.FirebaseUID).child("memory").set(self.data, config.FirebaseToken)
        except Exception:
            traceback.print_exc()

        # save locally as backup
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    # ---- Facts ----
    def remember_fact(self, text: str):
        text = str(text).strip()
        if text and text not in self.data["facts"]:
            self.data["facts"].append(text)
            self._save()
            return True
        return False

    def forget_fact(self, text: str):
        if text in self.data["facts"]:
            self.data["facts"].remove(text)
            self._save()
            return True
        # try substring match
        removed = [f for f in self.data["facts"] if text.lower() in f.lower()]
        if removed:
            self.data["facts"] = [f for f in self.data["facts"] if text.lower() not in f.lower()]
            self._save()
            return True
        return False

    # ---- Preferences ----
    def set_preference(self, key: str, value: str):
        key = str(key).strip().lower()
        self.data["preferences"][key] = str(value).strip()
        self._save()
        return True

    def get_preference(self, key: str, default=None):
        return self.data["preferences"].get(str(key).strip().lower(), default)

    def delete_preference(self, key: str):
        key = str(key).strip().lower()
        if key in self.data["preferences"]:
            del self.data["preferences"][key]
            self._save()
            return True
        return False

    # ---- Prompt Helper ----
    def prompt_block(self, username: str = "User") -> str:
        facts = self.data.get("facts", [])
        prefs = self.data.get("preferences", {})
        if not facts and not prefs:
            return f"User profile for {username}: (no saved memory yet)."

        lines = [f"User profile for {username}:"]
        if prefs:
            lines.append("Preferences: " + "; ".join([f"{k} = {v}" for k, v in prefs.items()]))
        if facts:
            lines.append("Facts: " + "; ".join(facts[:20]))
            if len(facts) > 20:
                lines.append(f"... (+{len(facts)-20} more facts)")
        return "\n".join(lines)

# -------- Convenience Functions --------
def get_memory_prompt(username="User"):
    return MemoryManager().prompt_block(username=username)

def remember(text: str):
    return MemoryManager().remember_fact(text)

def forget(text: str):
    return MemoryManager().forget_fact(text)

def set_preference(key: str, value: str):
    return MemoryManager().set_preference(key, value)

def delete_preference(key: str):
    return MemoryManager().delete_preference(key)
