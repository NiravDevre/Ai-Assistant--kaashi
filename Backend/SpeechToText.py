from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import dotenv_values
import os
import time
import mtranslate as mt
import threading
import tempfile

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
# get input language setting from the environment variables
InputLanguage = env_vars.get("InputLanguage", "en-US")

# Ensure Data directory exists
os.makedirs("Data", exist_ok=True)

#define the html code for speech recognition interface
HtmlCode = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <div id="status" style="color: blue; margin-top: 10px;"></div>
    <script>
        const output = document.getElementById('output');
        const status = document.getElementById('status');
        let recognition;
        let isListening = false;

        function startRecognition() {
            try {
                if ('webkitSpeechRecognition' in window) {
                    recognition = new webkitSpeechRecognition();
                } else if ('SpeechRecognition' in window) {
                    recognition = new SpeechRecognition();
                } else {
                    status.textContent = "Speech recognition not supported in this browser";
                    return;
                }

                recognition.lang = 'LANGUAGE_PLACEHOLDER';
                recognition.continuous = true;
                recognition.interimResults = false;
                recognition.maxAlternatives = 1;

                recognition.onstart = function() {
                    isListening = true;
                    status.textContent = "Listening...";
                };

                recognition.onresult = function(event) {
                    const transcript = event.results[event.results.length - 1][0].transcript.trim();
                    if (transcript) {
                        output.textContent = transcript;
                        status.textContent = "Speech captured: " + transcript;
                    }
                };

                recognition.onerror = function(event) {
                    status.textContent = "Error: " + event.error;
                    console.log('Speech recognition error:', event.error);
                };

                recognition.onend = function() {
                    isListening = false;
                    if (recognition && recognition.continuous) {
                        try {
                            recognition.start();
                        } catch (e) {
                            status.textContent = "Recognition ended: " + e.message;
                        }
                    } else {
                        status.textContent = "Recognition stopped";
                    }
                };
                
                recognition.start();
                
            } catch (error) {
                status.textContent = "Failed to start recognition: " + error.message;
            }
        }

        function stopRecognition() {
            try {
                if (recognition) {
                    recognition.continuous = false;
                    recognition.stop();
                    isListening = false;
                    status.textContent = "Recognition stopped";
                    output.textContent = "";
                }
            } catch (error) {
                status.textContent = "Error stopping recognition: " + error.message;
            }
        }

        // Add keyboard shortcuts
        document.addEventListener('keydown', function(event) {
            if (event.key === 's' && event.ctrlKey) {
                event.preventDefault();
                startRecognition();
            } else if (event.key === 'e' && event.ctrlKey) {
                event.preventDefault();
                stopRecognition();
            }
        });
    </script>
</body>
</html>'''

# Replace the language setting in the html code with the input language var
HtmlCode = HtmlCode.replace("LANGUAGE_PLACEHOLDER", InputLanguage)

# Write the modified html code to file
html_file_path = os.path.join("Data", "Voice.html")
try:
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(HtmlCode)
except Exception as e:
    print(f"Error writing HTML file: {e}")

# Get the current working directory
current_dir = os.getcwd()
# Generate the file path for the html file
Link = f"file:///{current_dir}/Data/Voice.html".replace("\\", "/")

# Set chrome options for the webdriver.
chrome_options = Options()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
chrome_options.add_argument(f'--user-agent={user_agent}')
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_argument("--use-fake-device-for-media-stream")
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--allow-running-insecure-content")
chrome_options.add_argument("--disable-features=VizDisplayCompositor")

# Global driver variable with thread lock
driver = None
driver_lock = threading.Lock()

def init_driver():
    """Initialize Chrome driver safely with better error handling"""
    global driver
    
    with driver_lock:
        if driver is None:
            try:
                print("Initializing Chrome WebDriver...")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(30)
                print("Chrome WebDriver initialized successfully")
                return True
            except Exception as e:
                print(f"Failed to initialize Chrome driver: {e}")
                return False
        return True

def cleanup_driver():
    """Safely cleanup driver"""
    global driver
    
    with driver_lock:
        if driver:
            try:
                driver.quit()
                print("Chrome WebDriver cleaned up")
            except Exception as e:
                print(f"Error during driver cleanup: {e}")
            finally:
                driver = None

# Define the path for temporary files
TempDirPath = os.path.join(current_dir, "Frontend", "Files")
os.makedirs(TempDirPath, exist_ok=True)

# function to set the assistant's status by writing it to a file
def SetAssistantStatus(Status):
    try:
        status_file = os.path.join(TempDirPath, 'Status.data')
        with open(status_file, "w", encoding='utf-8') as file:
            file.write(str(Status))
    except Exception as e:
        print(f"Error setting assistant status: {e}")

# function to modify a query to ensure proper punctuation and formatting
def QueryModifier(Query):
    if not Query or not isinstance(Query, str):
        return ""
        
    new_query = Query.lower().strip()
    if not new_query:
        return ""
        
    query_words = new_query.split()
    if not query_words:
        return ""
        
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    # check if the query is a question and add a question mark if necessary
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        # add a dot if the query is not a question
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()
    
# function to translate text to english using mtranslate
def UniversalTranslator(Text):
    try:
        if not Text or not isinstance(Text, str):
            return ""
            
        english_translation = mt.translate(Text, "en", "auto")
        return english_translation.capitalize() if english_translation else Text.capitalize()
    except Exception as e:
        print(f"Translation error: {e}")
        return Text.capitalize() if Text else ""

# function to perform speech recognition using the webdriver
def SpeechRecognition():
    user_query_path = os.path.join(TempDirPath, "UserQuery.data")
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # 1) QUICK CHECK before starting voice (handles already-typed text)
            if os.path.exists(user_query_path):
                with open(user_query_path, "r", encoding="utf-8") as f:
                    typed_text = f.read().strip()
                if typed_text:
                    # Clear the file after reading
                    with open(user_query_path, "w", encoding="utf-8") as f:
                        f.write("")
                    
                    if InputLanguage.lower().startswith("en"):
                        return QueryModifier(typed_text)
                    else:
                        SetAssistantStatus("Translating...")
                        return QueryModifier(UniversalTranslator(typed_text))

            # 2) Initialize driver if needed
            if not init_driver():
                SetAssistantStatus("Error: Could not initialize voice recognition")
                return "Error initializing voice recognition"

            # 3) Start voice recognition
            try:
                driver.get(Link)
                time.sleep(1)  # Wait for page to load
                
                start_button = driver.find_element(By.ID, "start")
                start_button.click()
                time.sleep(0.5)  # Give time for recognition to start
                
                SetAssistantStatus("Listening...")
                
            except Exception as e:
                print(f"Error starting recognition: {e}")
                retry_count += 1
                continue

            # 4) Main listening loop
            timeout_counter = 0
            max_timeout = 300  # 30 seconds (300 * 0.1)
            
            while timeout_counter < max_timeout:
                try:
                    # Check for typed input first
                    if os.path.exists(user_query_path):
                        with open(user_query_path, "r", encoding="utf-8") as f:
                            typed_text = f.read().strip()
                        if typed_text:
                            # Stop voice recognition cleanly
                            try:
                                end_button = driver.find_element(By.ID, "end")
                                end_button.click()
                            except Exception:
                                pass
                            
                            # Clear the file
                            with open(user_query_path, "w", encoding="utf-8") as f:
                                f.write("")

                            if InputLanguage.lower().startswith("en"):
                                return QueryModifier(typed_text)
                            else:
                                SetAssistantStatus("Translating...")
                                return QueryModifier(UniversalTranslator(typed_text))

                    # Check for voice input
                    output_element = driver.find_element(By.ID, "output")
                    text = output_element.text.strip()
                    
                    if text:
                        # Stop recognition
                        try:
                            end_button = driver.find_element(By.ID, "end")
                            end_button.click()
                        except Exception:
                            pass
                        
                        if InputLanguage.lower().startswith("en"):
                            return QueryModifier(text)
                        else:
                            SetAssistantStatus("Translating...")
                            return QueryModifier(UniversalTranslator(text))

                    # Small delay to avoid busy loop
                    time.sleep(0.1)
                    timeout_counter += 1

                except Exception as inner_e:
                    print(f"Error in listening loop: {inner_e}")
                    time.sleep(0.1)
                    timeout_counter += 1
                    continue

            # If we reach here, we timed out
            print("Speech recognition timed out")
            SetAssistantStatus("No input detected, please try again")
            return "timeout"

        except Exception as e:
            print(f"Speech recognition error (attempt {retry_count + 1}): {e}")
            retry_count += 1
            
            if retry_count < max_retries:
                print(f"Retrying... ({retry_count}/{max_retries})")
                # Cleanup and reinitialize
                cleanup_driver()
                time.sleep(1)
            else:
                SetAssistantStatus("Voice recognition failed")
                return "Error in speech recognition"

    return "Max retries reached"

# Cleanup function to be called on exit
def cleanup_speech_resources():
    """Clean up speech recognition resources"""
    cleanup_driver()
    
    # Clean up temporary files
    try:
        temp_files = ["Voice.html"]
        for temp_file in temp_files:
            file_path = os.path.join("Data", temp_file)
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        print(f"Error cleaning up temp files: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_speech_resources)

# main execution block.
if __name__ == "__main__":
    print("Speech Recognition Test Mode")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            print("\n" + "="*50)
            print("Waiting for speech input...")
            text = SpeechRecognition()
            print(f"Recognized: {text}")
            
            if text.lower() in ['exit', 'quit', 'stop']:
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup_speech_resources()
        print("Cleanup completed.")