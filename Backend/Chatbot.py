from groq import Groq
from dotenv import dotenv_values
import datetime
import traceback
import config
from Backend.Memory import get_memory_prompt
import pyrebase
from firebaseConfig import firebaseConfig

# Initialize Firebase
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# Load environment variables
env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname", "Kashi AI")
GroqAPIKey = env_vars.get("GroqAPIKey")

# Groq client
client = Groq(api_key=GroqAPIKey)

# System prompt
System = f"""Hello, I am {config.Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

SystemChatBot = [{"role": "system", "content": System}]


# ---------- Firebase Helpers ----------
def get_user_chatlog():
    """Get per-user chat history from Firebase."""
    try:
        data = db.child("users").child(config.FirebaseUID).child("chatlog").get(config.FirebaseToken).val()
        return data if data else []
    except Exception:
        traceback.print_exc()
        return []


def save_user_chatlog(messages: list):
    """Save per-user chat history to Firebase."""
    try:
        db.child("users").child(config.FirebaseUID).child("chatlog").set(messages, config.FirebaseToken)
    except Exception:
        traceback.print_exc()


def append_global_chat(role: str, content: str):
    """Append chat to global log (for training/stats)."""
    try:
        entry = {"uid": config.FirebaseUID, "username": config.Username, "role": role, "content": content}
        # note: global can allow broader write rules
        db.child("global").child("chatlog").push(entry, config.FirebaseToken)
    except Exception:
        traceback.print_exc()


# ---------- Utility ----------
def RealtimeInformation():
    current_date_time = datetime.datetime.now()
    return (
        f"Please use this real-time information if needed,\n"
        f"Day: {current_date_time.strftime('%A')}\n"
        f"Date: {current_date_time.strftime('%d')}\n"
        f"Month: {current_date_time.strftime('%B')}\n"
        f"Year: {current_date_time.strftime('%Y')}\n"
        f"Time: {current_date_time.strftime('%H')} hours : "
        f"{current_date_time.strftime('%M')} minutes :"
        f"{current_date_time.strftime('%S')} seconds.\n"
    )


def AnswerModifier(Answer: str):
    lines = Answer.split('\n')
    non_empty = [line.strip() for line in lines if line.strip()]
    return '\n'.join(non_empty)


# ---------- Main ChatBot ----------
def ChatBot(Query: str):
    """Handles a single chatbot query with Firebase-based history."""

    try:
        # load chatlog
        messages = get_user_chatlog()

        # append user query
        memory_prompt = {"role": "system", "content": get_memory_prompt(config.Username)}
        messages.append({"role": "user", "content": Query})

        # also save globally
        append_global_chat("user", Query)

        # request from Groq
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=SystemChatBot + [memory_prompt] + [{"role": "system", "content": RealtimeInformation()}] + messages,
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stream=True,
        )

        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.replace("</s>", "").strip()

        # append assistant response
        messages.append({"role": "assistant", "content": Answer})
        save_user_chatlog(messages)

        # save global
        append_global_chat("assistant", Answer)

        return AnswerModifier(Answer)

    except Exception as e:
        traceback.print_exc()
        return f"Sorry, something went wrong: {e}"


if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        print(ChatBot(user_input))
