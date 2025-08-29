# # Import required libraries
# from AppOpener import close, open as appopen  # Import functions to open and close apps.
from webbrowser import open as webopen  # Import web browser functionality.
from pywhatkit import search, playonyt  # Import functions for Google search and YouTube playback.
from dotenv import dotenv_values  # Import dotenv to manage environment variables.
from bs4 import BeautifulSoup  # Import BeautifulSoup for parsing HTML content.
from rich import print  # Import rich for styled console output.
from groq import Groq  # Import Groq for AI chat functionalities.
from Backend.VisionAnalysis import analyze_media

import webbrowser  # Import webbrowser for opening URLs.
import subprocess  # Import subprocess for interacting with the system.
import requests  # Import requests for making HTTP requests.
import keyboard  # Import keyboard for keyboard-related actions.
import asyncio  # Import asyncio for asynchronous programming.
import os  # Import os for operating system functionalities.
import urllib.parse
import json

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
GroqAPIKey = env_vars.get("GroqAPIKey")  # Retrieve the Groq API key.

# Define CSS classes for parsing specific elements in HTML content.
classes = [
    "ZCubwf", "hgKELc", "LTKOO sY7ric", "Z0LCw", "gsrt vk_bk FzvWSb YwPhnf", "pclqee", "tw-Data-text tw-text-small tw-ta",
    "IZ6rdc", "OSuR0d LTKOO", "vlzY6d", "webanswers-webanswers_table__webanswers-table", "dDoNo ikb4Bb gsrt", "sXLa0e",
    "LWkFke", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"
]

# Define a user-agent for making web requests.
useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'

# Initialize the Groq client with the API key.
client = Groq(api_key=GroqAPIKey)

# Predefined professional responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need—don't hesitate to ask.",
]

# List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{
    "role": "system",
    "content": f"Hello, I am {os.environ['Username']}, You're a content writer. You have to write content like letters, articles, and blogs."
}]

# Function to perform a Google search.
def GoogleSearch(Topic):
    search(Topic)  # Use pywhatkit's search function to perform a Google search.
    return True  # Indicate success.

# Function to generate content using AI and save it to a file.
def Content(Topic):

    # Nested function to open a file in Notepad.
    def OpenNotepad(File):
        default_text_editor = 'notepad.exe'  # Default text editor.
        subprocess.Popen([default_text_editor, File])  # Open the file in Notepad.

    # Nested function to generate content using the AI chatbot.
    def ContentWriterAI(prompt):
        messages.append({"role": "user", "content": f"{prompt}"})  # Add the user's prompt to messages.

        completion = client.chat.completions.create(
            model="llama3-70b-8192",  # Specify the AI model.
            messages=SystemChatBot + messages,  # Include system instructions and chat history.
            max_tokens=2048,  # Limit the maximum tokens in the response.
            temperature=0.7,  # Adjust response randomness.
            top_p=1,  # Use nucleus sampling for response diversity.
            stream=True,  # Enable streaming response.
            stop=None  # Allow the model to determine stopping conditions.
        )

        Answer = ""  # Initialize an empty string for the response.

        # Process streamed response chunks.
        for chunk in completion:
            if chunk.choices[0].delta.content:  # Check for content in the current chunk.
                Answer += chunk.choices[0].delta.content  # Append the content to the answer.

        Answer = Answer.replace("</s>", "")  # Remove unwanted tokens from the response.
        messages.append({"role": "assistant", "content": Answer})  # Add the AI's response to messages.
        return Answer

    Topic: str = Topic.replace("Content ", "")  # Remove "Content " from the topic.
    ContentByAI = ContentWriterAI(Topic)  # Generate content using AI.
    
    # Save the generated content to a text file.
    with open(rf"Data\{Topic.lower().replace(' ', '')}.txt", "w", encoding="utf-8") as file:
        file.write(ContentByAI)  # Write the content to the file.
        file.close()

    OpenNotepad(rf"Data\{Topic.lower().replace(' ', '')}.txt")  # Open the file in Notepad.
    return True  # Indicate success.

def YouTubeSearch(Topic):
    Url4Search = f"https://www.youtube.com/results?search_query={Topic}"  # Construct the YouTube search URL.
    webbrowser.open(Url4Search)  # Open the search URL in a web browser.
    return True  # Indicate success.

# Function to play a video on YouTube.
def PlayYoutube(query):
    playonyt(query)  # Use pywhatkit's playonyt function to play the video.
    return True  # Indicate success.

# Dictionary of popular apps and their official websites



APP_WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "facebook": "https://www.facebook.com",
    "instagram": "https://www.instagram.com",
    "chatgpt": "https://chatgpt.com",
    "x": "https://x.com",
    "whatsapp": "https://www.whatsapp.com",
    "wikipedia": "https://www.wikipedia.org",
    "reddit": "https://www.reddit.com",
    "yahoo_jp": "https://www.yahoo.co.jp",
    "yahoo": "https://www.yahoo.com",
    "yandex": "https://www.yandex.ru",
    "tiktok": "https://www.tiktok.com",
    "amazon": "https://www.amazon.com",
    "baidu": "https://www.baidu.com",
    "microsoftonline": "https://www.microsoftonline.com",
    "linkedin": "https://www.linkedin.com",
    "pornhub": "https://www.pornhub.com",
    "netflix": "https://www.netflix.com",
    "naver": "https://www.naver.com",
    "live": "https://www.live.com",
    "dzen": "https://dzen.ru",
    "office": "https://www.office.com",
    "bing": "https://www.bing.com",
    "temu": "https://www.temu.com",
    "pinterest": "https://www.pinterest.com",
    "bilibili": "https://www.bilibili.com",
    "xvideos": "https://www.xvideos.com",
    "microsoft": "https://www.microsoft.com",
    "twitch": "https://www.twitch.tv",
    "xhamster": "https://www.xhamster.com",
    "vk": "https://vk.com",
    "mailru": "https://mail.ru",
    "news_yahoo_jp": "https://news.yahoo.co.jp",
    "sharepoint": "https://www.sharepoint.com",
    "fandom": "https://www.fandom.com",
    "globo": "https://www.globo.com",
    "canva": "https://www.canva.com",
    "weather": "https://www.weather.com",
    "samsung": "https://www.samsung.com",
    "telegram": "https://t.me",
    "duckduckgo": "https://www.duckduckgo.com",
    "openai": "https://www.openai.com",
    "xnxx": "https://www.xnxx.com",
    "nytimes": "https://www.nytimes.com",
    "stripchat": "https://www.stripchat.com",
    "zoom": "https://zoom.us",
    "aliexpress": "https://www.aliexpress.com",
    "roblox": "https://www.roblox.com",
    "espncricinfo": "https://www.espncricinfo.com",
    "cricbuzz": "https://www.cricbuzz.com",
    "apple": "https://www.apple.com",
    # ... continue adding up to 200 entries
}


# def OpenApp(app, sess=requests.session()):
#     try:
#         appopen(app, match_closest=True, output=True, throw_error=True)
#         return True

#     except Exception as e:
#         print(f"Could not open app directly: {e}")

#         app_lower = app.lower()
#         if app_lower in APP_WEBSITES:
#             url = APP_WEBSITES[app_lower]
#             print(f"Opening official website for {app}: {url}")
#             webbrowser.open(url)
#             return True

#         # If not found, do a Google search and open the first relevant result
#         headers = {"User-Agent": "Mozilla/5.0"}
#         search_url = f"https://www.google.com/search?q={urllib.parse.quote(app)}"
#         response = sess.get(search_url, headers=headers)
#         soup = BeautifulSoup(response.text, "html.parser")

#         for a in soup.find_all("a", href=True):
#             href = a['href']
#             if href.startswith("/url?q="):
#                 url = href.split("/url?q=")[1].split("&")[0]
#                 url = urllib.parse.unquote(url)
#                 # Open the first valid URL (skip google internal links)
#                 if not url.startswith("https://webcache.googleusercontent.com") and not url.startswith("https://policies.google.com"):
#                     print(f"Opening first search result URL: {url}")
#                     webbrowser.open(url)
#                     return True

#         print(f"No suitable URL found for {app}")
#         return False

# # Function to close an application.
# def CloseApp(app):
#     if "chrome" in app:
#         pass  # Skip if the app is Chrome.
#     else:
#         try:
#             close(app, match_closest=True, output=True, throw_error=True)  # Attempt to close the app.
#             return True  # Indicate success.
#         except:
#             return False

# Function to execute system-level commands.
def System(command):
    # Nested function to mute the system volume.
    def mute():
        keyboard.press_and_release("volume mute")  # Simulate the mute key press.

    # Nested function to unmute the system volume.
    def unmute():
        keyboard.press_and_release("volume mute")  # Simulate the unmute key press.

    # Nested function to increase the system volume.
    def volume_up():
        keyboard.press_and_release("volume up")  # Simulate the volume up key press.

    # Nested function to decrease the system volume.
    def volume_down():
        keyboard.press_and_release("volume down")  # Simulate the volume down key press.

    # Execute the appropriate command.
    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()

    return True  # Indicate success.

def AnalyzeMedia(command):
    """
    Analyze images and files using the VisionAnalysis module
    """
    try:
        # Extract file path and question from command
        parts = command.split(' ', 2)  # Split into max 3 parts
        if len(parts) < 2:
            return "Please provide a file path to analyze."
        
        file_path = parts[1]  # The file path
        question = parts[2] if len(parts) > 2 else None  # Optional question
        
        # Use the vision analysis module
        result = analyze_media(file_path, question)
        return result
        
    except Exception as e:
        return f"Error analyzing media: {str(e)}"

# Asynchronous function to translate and execute user commands.
async def TranslateAndExecute(commands: list[str]):
    funcs = []  # List to store asynchronous tasks.

    for command in commands:
        if command.startswith("open "):  # Handle "open" commands.
            if "open it" in command:  # Ignore "open it" commands.
                pass
            if "open file" == command:  # Ignore "open file" commands.
                pass
            else:
                fun = asyncio.to_thread(OpenApp, command.removeprefix("open "))  # Schedule app opening.
                funcs.append(fun)

        elif command.startswith("general "):  # Placeholder for general commands.
            pass

        elif command.startswith("realtime "):  # Placeholder for real-time commands.
            pass

        elif command.startswith("close "):  # Handle "close" commands.
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close "))  # Schedule app closing.
            funcs.append(fun)

        elif command.startswith("play "):  # Handle "play" commands.
            fun = asyncio.to_thread(PlayYoutube, command.removeprefix("play "))  # Schedule YouTube playback.
            funcs.append(fun)
        
        elif command.startswith("content "):  # Handle "content" commands.
            fun = asyncio.to_thread(Content, command.removeprefix("content "))
            funcs.append(fun)

        elif command.startswith("google search "):
            fun = asyncio.to_thread(GoogleSearch, command.removeprefix("google search "))
            funcs.append(fun)

        elif command.startswith("youtube search "):
            fun = asyncio.to_thread(YouTubeSearch, command.removeprefix("youtube search "))
            funcs.append(fun)

        elif command.startswith("system "):
            fun = asyncio.to_thread(System, command.removeprefix("system "))
            funcs.append(fun)
        
        # ADD THESE NEW CONDITIONS:
        elif command.startswith("analyze image "):  # Handle image analysis
            fun = asyncio.to_thread(AnalyzeMedia, command)
            funcs.append(fun)
        
        elif command.startswith("analyze file "):  # Handle file analysis
            fun = asyncio.to_thread(AnalyzeMedia, command)
            funcs.append(fun)
        
        elif command.startswith("read image "):  # Alternative for image OCR
            # Convert to analyze image command
            new_command = command.replace("read image ", "analyze image ")
            fun = asyncio.to_thread(AnalyzeMedia, new_command)
            funcs.append(fun)
        
        elif command.startswith("read document "):  # Alternative for document reading
            # Convert to analyze file command
            new_command = command.replace("read document ", "analyze file ")
            fun = asyncio.to_thread(AnalyzeMedia, new_command)
            funcs.append(fun)
        
        else:
            print(f"No Function Found. For {command}")

    results = await asyncio.gather(*funcs)

    for result in results:
        if isinstance(result, str):
            yield result
        else:
            yield result

# Asynchronous function to automate command execution.
async def Automation(commands: list[str]):
    async for result in TranslateAndExecute(commands):  # Translate and execute commands.
        pass

    return True  # Indicate success.
