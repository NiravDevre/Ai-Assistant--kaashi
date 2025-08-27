from googlesearch import search
from dotenv import dotenv_values
from groq import Groq
import datetime, traceback, config
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

# System instruction
System = f"""Hello, I am {config.Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""

SystemChatBot = [{"role": "system", "content": System}]

# ----------------- Firebase Helpers -----------------
def get_user_chatlog():
    try:
        data = db.child("users").child(config.FirebaseUID).child("chatlog").get(config.FirebaseToken).val()
        return data if data else []
    except Exception:
        traceback.print_exc()
        return []

def save_user_chatlog(messages):
    try:
        db.child("users").child(config.FirebaseUID).child("chatlog").set(messages, config.FirebaseToken)
    except Exception:
        traceback.print_exc()

def append_global_chat(role, content):
    try:
        entry = {"uid": config.FirebaseUID, "username": config.Username, "role": role, "content": content}
        db.child("global").child("chatlog").push(entry, config.FirebaseToken)
    except Exception:
        traceback.print_exc()

# ----------------- Utilities -----------------
def GoogleSearch(query):
    results = list(search(query, advanced=True, num_results=3))
    Answer = f"The search results for '{query}' are:\n[start]\n"
    for i in results:
        Answer += f"Title: {i.title}\nDescription: {i.description}\n\n"
    Answer += "[end]"
    return Answer

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

def Information(): 
    now = datetime.datetime.now()
    return (
        f"Please use this real-time information if needed,\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
        f"Time: {now.strftime('%H')} hours : {now.strftime('%M')} minutes : {now.strftime('%S')} seconds.\n"
    )

# ----------------- Main Engine -----------------
def RealtimeSearchEngine(prompt):
    global SystemChatBot
    try:
        # load chatlog for this user
        messages = get_user_chatlog()

        # add user query
        messages.append({"role": "user", "content": prompt})
        save_user_chatlog(messages)
        append_global_chat("user", prompt)

        # add Google results
        SystemChatBot.append({"role": "user", "content": GoogleSearch(prompt)})

        # Groq API call
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=SystemChatBot + [{"role": "system", "content": Information()}] + messages,
            max_tokens=2048,
            temperature=0.7,
            top_p=1,
            stream=True
        )

        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content

        Answer = Answer.replace("</s>", "").strip()

        # save assistant reply
        messages.append({"role": "assistant", "content": Answer})
        save_user_chatlog(messages)
        append_global_chat("assistant", Answer)

        # cleanup SystemChatBot (remove Google results injection)
        SystemChatBot.pop()

        return AnswerModifier(Answer)

    except Exception as e:
        traceback.print_exc()
        return f"Realtime search failed: {e}"

# ----------------- CLI Test -----------------
if __name__ == "__main__":
    while True:
        user_input = input("Enter Your query: ")
        print(RealtimeSearchEngine(user_input))
