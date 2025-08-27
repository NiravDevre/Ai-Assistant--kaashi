# === Main Controller (Refactored & Fixed) ===
from Frontend.Gui import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    AnswerModifier,
    QueryModifier,
    GetMicrophoneStatus,
    GetAssistantStatus,
    MicButtonInitialized
)
from Frontend.LoginScreen import LoginWindow, has_valid_token
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, pyqtSignal
from Backend.Model import FirstLayerDMM
from Backend.RealTimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from Backend.ImageGenration import generate_image, generate_multiple_images
from Backend.Memory import remember as remember_memory, forget as forget_memory, set_preference as set_pref

from config import TOKEN_FILE
import config
from langdetect import detect
from dotenv import dotenv_values
from asyncio import run, get_event_loop, to_thread, gather, wait_for, TimeoutError, new_event_loop, set_event_loop
from time import sleep
import subprocess
import numpy as np
import pyaudio
import threading
import json
import os
import traceback
import sys
import signal

# Firebase
import pyrebase
from firebaseConfig import firebaseConfig
firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# ---------------------- Env & constants ----------------------
env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname", "Assistant")

AUTOMATION_FUNCS = {"open", "close", "play", "system", "content", "google search", "youtube search"}
REALTIME_KEYWORDS = ["today", "current", "latest", "breaking", "recent", "now", "weather", "price", "score", "update"]
WAKE_WORDS = ["kashi", "काशी", "कासी", "hey assistant", "wake up", "hello ai", "__snap__"]

# Audio settings for snap detection
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SNAP_THRESHOLD = 8000

# Global variables
gui_app = None
main_window = None
login_window = None
voice_thread = None
query_thread = None
shutdown_event = threading.Event()

# ---------------------- Firebase Helper Functions ----------------------
def ensure_valid_token():
    """Ensures that config.FirebaseToken is valid and refreshed."""
    if not config.FirebaseToken:
        result = has_valid_token()
        if result:
            username, uid, token = result
            config.Username = username
            config.FirebaseUID = uid
            config.FirebaseToken = token
    return config.FirebaseToken

def get_user_chatlog():
    """Get user's chat history from Firebase"""
    token = ensure_valid_token()
    uid = config.FirebaseUID
    if not token or not uid:
        return []
    try:
        data = db.child("chats").child("users").child(uid).get(token).val()
        return data if data else []
    except Exception as e:
        print(f"Error getting chat log: {e}")
        return []

def save_user_chatlog(messages: list):
    """Save user's chat history to Firebase"""
    token = ensure_valid_token()
    uid = config.FirebaseUID
    if token and uid:
        try:
            db.child("chats").child("users").child(uid).set(messages, token)
        except Exception as e:
            print(f"Error saving chat log: {e}")

def append_global_chat(username, role, content):
    """Append message to global chat log"""
    token = ensure_valid_token()
    if token:
        try:
            db.child("chats").child("global").push({
                "user": username,
                "role": role,
                "content": content
            }, token)
        except Exception as e:
            print(f"Error appending to global chat: {e}")

def ShowDefaultChatIfNoChats(username):
    """Show default greeting if no chat history exists"""
    messages = get_user_chatlog()
    if not messages:
        default_messages = [
            {"role": "user", "content": f"Hello {Assistantname}, How are you?"},
            {"role": "assistant", "content": f"Welcome {username}. I am doing well. How may I help you?"}
        ]
        save_user_chatlog(default_messages)

def ShowChatsOnGUI(username):
    """Display chat history on GUI"""
    try:
        messages = get_user_chatlog()
        formatted = []
        for entry in messages:
            if entry["role"] == "user":
                formatted.append(f"{username} : {entry['content']}")
            elif entry["role"] == "assistant":
                formatted.append(f"{Assistantname} : {entry['content']}")
        if formatted:
            ShowTextToScreen("\n".join(formatted))
    except Exception as e:
        print(f"Error showing chats on GUI: {e}")

def InitialExecution(username):
    """Initialize the application after successful login"""
    print(f"Initializing application for user: {username}")
    try:
        SetMicrophoneStatus("False")
        ShowTextToScreen("")
        ShowDefaultChatIfNoChats(username)
        ShowChatsOnGUI(username)
        print("Initial execution completed successfully")
    except Exception as e:
        print(f"Error in InitialExecution: {e}")
        traceback.print_exc()

# ---------------------- Decision Parsing ----------------------
def parse_decisions(decisions: list):
    """Parse AI decisions into different task buckets"""
    buckets = {"automation": [], "general": [], "realtime": [], "images": [], "exit": False}
    
    if not decisions:
        return buckets
        
    for d in decisions:
        if not d or not isinstance(d, str):
            continue
            
        low = d.lower().strip()
        if low == "exit":
            buckets["exit"] = True
            continue
            
        if low.startswith("generate image "):
            buckets["images"].append(d[len("generate image "):].strip())
            continue
            
        head = low.split(" ", 1)[0] if " " in low else low

        # Force 'realtime' to 'general' unless it contains fresh info keywords
        if low.startswith("realtime "):
            query_content = d[len("realtime "):].strip()
            if any(k in low for k in REALTIME_KEYWORDS):
                buckets["realtime"].append(query_content)
            else:
                buckets["general"].append(query_content)
        elif head in AUTOMATION_FUNCS:
            buckets["automation"].append(d)
        elif low.startswith("general "):
            buckets["general"].append(d[len("general "):].strip())
        else:
            # Default to general for unrecognized patterns
            buckets["general"].append(d)
    
    return buckets

# ---------------------- Async Task Runners ----------------------
async def run_automation(decisions):
    if not decisions:
        return None
    try:
        SetAssistantStatus("Working on automation...")
        result = await wait_for(Automation(decisions), timeout=60)
        return "Automation completed successfully." if result else "Automation completed."
    except TimeoutError:
        return "Automation timed out."
    except Exception as e:
        traceback.print_exc()
        return f"Automation failed: {str(e)}"

async def run_general(queries):
    if not queries:
        return []
    
    SetAssistantStatus("Thinking...")
    
    async def one(q):
        try:
            modified_query = QueryModifier(q)
            return await wait_for(to_thread(ChatBot, modified_query), timeout=45)
        except TimeoutError:
            return f"'{q}' timed out."
        except Exception as e:
            traceback.print_exc()
            return f"'{q}' failed: {str(e)}"
    
    return await gather(*[one(q) for q in queries], return_exceptions=True)

async def run_realtime(queries):
    if not queries:
        return []
    
    SetAssistantStatus("Searching...")
    
    async def one(q):
        try:
            modified_query = QueryModifier(q)
            return await wait_for(to_thread(RealtimeSearchEngine, modified_query), timeout=60)
        except TimeoutError:
            return f"'{q}' timed out."
        except Exception as e:
            traceback.print_exc()
            return f"'{q}' failed: {str(e)}"
    
    return await gather(*[one(q) for q in queries], return_exceptions=True)

async def run_images(prompts):
    if not prompts:
        return []
    
    SetAssistantStatus("Generating images...")
    
    async def one(p, idx):
        try:
            path = await wait_for(to_thread(generate_image, p, idx+1), timeout=90)
            return #f"[Image saved: {path}]" if path else f"[Image for '{p}' failed]"
        except TimeoutError:
            return #f"[Image for '{p}' timed out]"
        except Exception as e:
            traceback.print_exc()
            return #f"[Image for '{p}' failed: {str(e)}]"
    
    return await gather(*[one(p, i) for i, p in enumerate(prompts)], return_exceptions=True)

def merge_answers(realtime_answers, general_answers):
    """Merge answers from different sources"""
    parts = []
    
    if realtime_answers:
        for a in realtime_answers:
            if a and not isinstance(a, Exception):
                modified = AnswerModifier(str(a))
                if modified:
                    parts.append(str(modified))
    
    if general_answers:
        for a in general_answers:
            if a and not isinstance(a, Exception):
                modified = AnswerModifier(str(a))
                if modified:
                    parts.append(str(modified))
    
    return "\n\n".join(parts).strip()

# ---------------------- TTS Wrapper ----------------------
def safe_tts(text: str, lang="en"):
    """Safe text-to-speech wrapper"""
    try:
        if text and str(text).strip():
            SetAssistantStatus("Answering...")
            TextToSpeech(str(text), lang=lang)
    except Exception as e:
        print(f"TTS Error: {e}")
        traceback.print_exc()

# ---------------------- Main Execution ----------------------
def MainExecution(Query: str, lang="en"):
    """Main query processing function"""
    username = config.Username
    if not username:
        print("No username set, cannot process query")
        return False

    if not Query or not Query.strip():
        print("Empty query received")
        return False

    try:
        SetAssistantStatus("Listening...")
        ShowTextToScreen(f'{username} : {Query}')
        SetAssistantStatus("Thinking...")

        # Get decisions from AI
        try:
            decisions = FirstLayerDMM(Query)
        except Exception as e:
            traceback.print_exc()
            error_msg = f"Sorry, I couldn't process that: {str(e)}"
            ShowTextToScreen(f"{Assistantname} : {error_msg}")
            safe_tts("Sorry, I couldn't process that request.", lang)
            return True

        if not decisions:
            error_msg = "I'm not sure how to help with that."
            ShowTextToScreen(f"{Assistantname} : {error_msg}")
            safe_tts(error_msg, lang)
            return True

        buckets = parse_decisions(decisions)

        if buckets["exit"]:
            farewell = "Okay, bye!"
            ShowTextToScreen(f"{Assistantname} : {farewell}")
            safe_tts(farewell, lang)
            cleanup_and_exit()

        # Orchestrate async tasks
        async def orchestrate():
            results = {}
            
            # Run tasks concurrently where possible
            tasks = []
            
            if buckets["automation"]:
                tasks.append(("automation", run_automation(buckets["automation"])))
            if buckets["realtime"]:
                tasks.append(("realtime", run_realtime(buckets["realtime"])))
            if buckets["general"]:
                tasks.append(("general", run_general(buckets["general"])))
            if buckets["images"]:
                tasks.append(("images", run_images(buckets["images"])))
            
            # Wait for all tasks
            for task_name, task_coro in tasks:
                try:
                    results[task_name] = await task_coro
                except Exception as e:
                    print(f"Error in {task_name} task: {e}")
                    results[task_name] = f"Error in {task_name}: {str(e)}"
            
            # Merge answers
            combined = merge_answers(
                results.get("realtime", []), 
                results.get("general", [])
            )
            
            if not combined:
                combined = results.get("automation") or "Done."
            
            # Add image results if any
            if results.get("images"):
                image_results = [str(img) for img in results["images"] if img]
                if image_results:
                    combined += "\n\n" + "\n".join(image_results)
            
            return combined

        # Run the orchestration
        try:
            # Get or create event loop
            try:
                loop = get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                loop = new_event_loop()
                set_event_loop(loop)

            final_answer = loop.run_until_complete(orchestrate())
            
        except Exception as e:
            traceback.print_exc()
            final_answer = f"Something went wrong while processing tasks: {str(e)}"

        # Process and display final answer
        final_answer = AnswerModifier(str(final_answer or ""))
        if final_answer and final_answer.strip():
            ShowTextToScreen(f"{Assistantname} : {final_answer}")
            safe_tts(final_answer, lang)

            # Save to Firebase history
            try:
                messages = get_user_chatlog()
                messages.append({"role": "user", "content": Query})
                messages.append({"role": "assistant", "content": final_answer})
                save_user_chatlog(messages)
                append_global_chat(username, "assistant", final_answer)
            except Exception as e:
                print(f"Error saving to Firebase: {e}")
        else:
            fallback_msg = "I've completed your request."
            ShowTextToScreen(f"{Assistantname} : {fallback_msg}")
            safe_tts(fallback_msg, lang)

        return True

    except Exception as e:
        print(f"Error in MainExecution: {e}")
        traceback.print_exc()
        
        error_msg = "I encountered an error processing your request."
        ShowTextToScreen(f"{Assistantname} : {error_msg}")
        safe_tts(error_msg, lang)
        return False

# ---------------------- Wake Detection ----------------------
def detect_snap():
    """Detect snap sound for wake-up"""
    if shutdown_event.is_set():
        return False
        
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(format=FORMAT, channels=CHANNELS,
                            rate=RATE, input=True,
                            frames_per_buffer=CHUNK)
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        peak = np.abs(data).max()
        stream.stop_stream()
        stream.close()
        audio.terminate()
        return peak > SNAP_THRESHOLD
    except Exception as e:
        print(f"Snap detection error: {e}")
        return False

def detect_wake():
    """Detect wake words or snap"""
    if shutdown_event.is_set():
        return False
        
    try:
        word = SpeechRecognition()
        if not word or word.lower() in ["timeout", "error in speech recognition", "max retries reached"]:
            return False
            
        word_lower = word.lower()
        print(f"Heard: {word}")
        
        if any(w in word_lower for w in WAKE_WORDS if w != "__snap__"):
            return True
            
    except Exception as e:
        print(f"Speech detection error: {e}")
    
    # Check for snap
    if "__snap__" in WAKE_WORDS and detect_snap():
        print("Snap detected.")
        return True
        
    return False

# ---------------------- Language Support ----------------------
current_tts_lang = "en"
LANG_NAME_TO_CODE = {
    "english": "en",
    "hindi": "hi", 
    "gujarati": "gu",
    "french": "fr",
    "spanish": "es",
    "tamil": "ta",
    "telugu": "te",
    "bengali": "bn",
    "malayalam": "ml",
    "marathi": "mr"
}

def try_change_language(command: str):
    """Try to change TTS language based on command"""
    global current_tts_lang
    
    if not command:
        return False
        
    lower_cmd = command.lower()
    for lang_name, code in LANG_NAME_TO_CODE.items():
        if f"speak in {lang_name}" in lower_cmd or f"change language to {lang_name}" in lower_cmd:
            current_tts_lang = code
            safe_tts(f"Okay, I will now speak in {lang_name}.", lang=current_tts_lang)
            return True
    return False

# ---------------------- Threading Functions ----------------------
def FirstThread():
    """Voice interaction thread"""
    global current_tts_lang
    wake_mode = False
    
    print("Voice thread started")
    
    while not shutdown_event.is_set():
        try:
            if not wake_mode:
                SetAssistantStatus("Waiting for call...")
                print("Say a wake word or snap...")
                
                if detect_wake():
                    try:
                        safe_tts("I am listening.", current_tts_lang)
                    except Exception as e:
                        print(f"Error in wake TTS: {e}")
                    
                    try:
                        MicButtonInitialized()
                    except Exception as e:
                        print(f"Error initializing mic button: {e}")
                    
                    wake_mode = True
                else:
                    sleep(0.5)  # Reduced sleep for better responsiveness
                    continue
            else:
                SetAssistantStatus("Listening...")
                print("Listening for command...")
                
                try:
                    command = SpeechRecognition()
                    
                    if not command or command.lower() in ["timeout", "error in speech recognition", "max retries reached"]:
                        print("No valid command received, continuing...")
                        sleep(0.1)
                        continue
                        
                    command_lower = command.lower()
                    print(f"Command: {command}")

                    # Check for language change
                    if try_change_language(command):
                        continue

                    # Detect language if needed
                    try:
                        lang_code = detect(command) if current_tts_lang == "en" else current_tts_lang
                    except:
                        lang_code = current_tts_lang

                    # Check for sleep command
                    if command_lower in ["go to sleep", "stop listening", "sleep mode"]:
                        safe_tts("Going to sleep.", lang_code)
                        wake_mode = False
                        continue

                    # Process command if microphone is active
                    current_status = GetMicrophoneStatus()
                    if str(current_status).lower() == "true":
                        MainExecution(command, lang=lang_code)
                    else:
                        try:
                            ai_status = GetAssistantStatus()
                            if "Available..." not in str(ai_status):
                                SetAssistantStatus("Available...")
                        except Exception as e:
                            print(f"Error setting status: {e}")
                            
                except Exception as e:
                    print(f"Command processing error: {e}")
                    try:
                        safe_tts("Sorry, I didn't catch that. Please repeat.", current_tts_lang)
                    except:
                        pass
                    
        except Exception as e:
            print(f"FirstThread error: {e}")
            if not shutdown_event.is_set():
                sleep(1)  # Prevent rapid error loops

    print("Voice thread shutting down")

# ---------------------- Query File Monitor ----------------------
def monitor_user_query():
    """Monitor for text input from GUI"""
    query_file = TempDirectoryPath("UserQuery.data")
    last_modified = 0
    
    print("Query monitor thread started")
    
    while not shutdown_event.is_set():
        try:
            if os.path.exists(query_file):
                current_modified = os.path.getmtime(query_file)
                if current_modified > last_modified:
                    last_modified = current_modified
                    
                    with open(query_file, "r", encoding="utf-8") as f:
                        query = f.read().strip()
                    
                    if query:
                        # Clear the file
                        with open(query_file, "w", encoding="utf-8") as f:
                            f.write("")
                        
                        # Process the query
                        try:
                            lang_code = detect(query) if current_tts_lang == "en" else current_tts_lang
                        except:
                            lang_code = current_tts_lang
                            
                        MainExecution(query, lang=lang_code)
            
            sleep(0.1)  # Check every 100ms
            
        except Exception as e:
            print(f"Query monitor error: {e}")
            if not shutdown_event.is_set():
                sleep(1)

    print("Query monitor thread shutting down")

# ---------------------- Cleanup Functions ----------------------
def cleanup_and_exit():
    """Clean shutdown of the application"""
    print("Starting application cleanup...")
    
    # Signal all threads to stop
    shutdown_event.set()
    
    # Stop TTS and cleanup resources
    try:
        from Backend.TextToSpeech import cleanup_all_temp_files
        cleanup_all_temp_files()
    except Exception as e:
        print(f"Error cleaning up TTS: {e}")
    
    # Cleanup speech recognition
    try:
        from Backend.SpeechToText import cleanup_speech_resources
        cleanup_speech_resources()
    except Exception as e:
        print(f"Error cleaning up speech recognition: {e}")
    
    # Close GUI
    if gui_app:
        try:
            gui_app.quit()
        except Exception as e:
            print(f"Error quitting GUI app: {e}")
    
    print("Cleanup completed, exiting...")
    sys.exit(0)

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print(f"Received signal {sig}, shutting down gracefully...")
    cleanup_and_exit()

# ---------------------- Main Application Entry Point ----------------------
def main():
    """Main application entry point"""
    global gui_app, login_window, main_window, voice_thread, query_thread
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting Kashi AI Assistant...")
    
    # Create QApplication
    gui_app = QApplication(sys.argv)
    gui_app.setApplicationName("Kashi AI")
    
    # Handle application quit
    gui_app.aboutToQuit.connect(cleanup_and_exit)
    
    def start_main_app(username, uid, token):
        """Start the main application after login"""
        global voice_thread, query_thread
        
        print(f"Starting main app for: {username}")
        
        # Set global config
        config.Username = username
        config.FirebaseUID = uid
        config.FirebaseToken = token
        
        # Initialize application
        try:
            InitialExecution(username)
        except Exception as e:
            print(f"Error in InitialExecution: {e}")
            QMessageBox.warning(None, "Initialization Warning", 
                              f"Some initialization steps failed: {str(e)}")
        
        # Start background threads
        try:
            voice_thread = threading.Thread(target=FirstThread, daemon=True, name="VoiceThread")
            voice_thread.start()
            print("Voice thread started")
        except Exception as e:
            print(f"Error starting voice thread: {e}")
        
        try:
            query_thread = threading.Thread(target=monitor_user_query, daemon=True, name="QueryThread")
            query_thread.start()
            print("Query monitor thread started")
        except Exception as e:
            print(f"Error starting query thread: {e}")
        
        # Close login window if it exists
        if login_window:
            try:
                login_window.close()
            except Exception as e:
                print(f"Error closing login window: {e}")
        
        # Create and show main GUI
        try:
            from Frontend.Gui import MainWindow
            main_window = MainWindow(get_user_chatlog, save_user_chatlog)
            main_window.show()
            print("Main window shown")
        except Exception as e:
            print(f"Error creating main window: {e}")
            QMessageBox.critical(None, "GUI Error", 
                               f"Failed to create main window: {str(e)}")
    
    try:
        # Check for existing valid token
        print("Checking for existing session...")
        token_result = has_valid_token()
        
        if token_result:
            username, uid, token = token_result
            print(f"Found valid session for: {username}")
            start_main_app(username, uid, token)
        else:
            print("No valid session found, showing login window...")
            # Show login window
            try:
                login_window = LoginWindow()
                login_window.login_success.connect(start_main_app)
                login_window.show()
            except Exception as e:
                print(f"Error creating login window: {e}")
                QMessageBox.critical(None, "Login Error", 
                                   f"Failed to create login window: {str(e)}")
                sys.exit(1)
        
        # Start the single event loop (this keeps the app running)
        print("Starting Qt event loop...")
        exit_code = gui_app.exec_()
        print(f"Qt event loop exited with code: {exit_code}")
        
        # Cleanup before final exit
        cleanup_and_exit()
        
    except Exception as e:
        print(f"Application startup error: {e}")
        traceback.print_exc()
        
        # Show error message
        try:
            if gui_app:
                QMessageBox.critical(None, "Startup Error", 
                                   f"Failed to start application:\n{str(e)}")
        except:
            pass
        
        cleanup_and_exit()

if __name__ == "__main__":
    main()