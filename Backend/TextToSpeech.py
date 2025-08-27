import pygame
import random
import asyncio
import edge_tts
import os
import tempfile
import time
import threading
from langdetect import detect
import atexit

# Voice map for supported languages
VOICE_MAP = {
    "en": "en-US-JennyNeural",
    "hi": "hi-IN-SwaraNeural",
    "gu": "gu-IN-DhwaniNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-MohanNeural",
    "bn": "bn-IN-TanishaaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "mr": "mr-IN-AarohiNeural"
}

# Global variables for thread safety
audio_lock = threading.Lock()
pygame_initialized = False
temp_files_created = []

def init_pygame():
    """Initialize pygame mixer safely"""
    global pygame_initialized
    
    if not pygame_initialized:
        try:
            # Stop any existing mixer
            try:
                pygame.mixer.quit()
            except:
                pass
                
            # Initialize with better settings
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            pygame_initialized = True
            print("Pygame mixer initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize pygame mixer: {e}")
            pygame_initialized = False
            return False
    return True

def cleanup_temp_file(file_path, max_retries=5):
    """Safely remove temp file with retry logic"""
    if not file_path or not os.path.exists(file_path):
        return True
        
    for attempt in range(max_retries):
        try:
            # Ensure pygame is not using the file
            if pygame_initialized:
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except:
                    pass
            
            # Wait a bit before attempting deletion
            time.sleep(0.1 + (attempt * 0.1))
            
            # Attempt to delete
            os.unlink(file_path)
            
            # Remove from tracking list
            if file_path in temp_files_created:
                temp_files_created.remove(file_path)
                
            return True
            
        except (PermissionError, OSError) as e:
            print(f"Attempt {attempt + 1}: Could not delete {file_path}: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.2 * (attempt + 1))  # Exponential backoff
        except Exception as e:
            print(f"Unexpected error deleting {file_path}: {e}")
            break
    
    print(f"Failed to delete temporary file: {file_path}")
    return False

def cleanup_all_temp_files():
    """Clean up all created temporary files"""
    global temp_files_created
    
    try:
        if pygame_initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except:
        pass
    
    for file_path in temp_files_created.copy():
        cleanup_temp_file(file_path)
    
    temp_files_created.clear()

# Register cleanup function for application exit
atexit.register(cleanup_all_temp_files)

async def TextToAudioFile(text, lang="en") -> str:
    """Convert text to audio file with better error handling"""
    if not text or not str(text).strip():
        raise ValueError("Text is empty or invalid")
    
    # Create unique temp file to avoid conflicts
    temp_fd, temp_path = tempfile.mkstemp(suffix='.mp3', prefix='tts_', dir=None)
    os.close(temp_fd)  # Close file descriptor immediately to avoid locks
    
    # Add to tracking list
    temp_files_created.append(temp_path)
    
    voice = VOICE_MAP.get(lang, VOICE_MAP["en"])
    print(f"[TTS] Using voice: {voice} for language: {lang}")

    try:
        # Create the TTS communication object
        communicate = edge_tts.Communicate(
            text=str(text), 
            voice=voice, 
            pitch='+7Hz', 
            rate='+13%'
        )
        
        # Save the audio file
        await communicate.save(temp_path)
        
        # Verify file was created and has content
        if not os.path.exists(temp_path):
            raise Exception("Audio file was not created")
            
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            raise Exception("Audio file is empty")
        
        print(f"[TTS] Audio file created: {os.path.basename(temp_path)} ({file_size} bytes)")
        return temp_path
        
    except Exception as e:
        print(f"Error with voice '{voice}': {e}")
        
        # Try fallback to English voice
        try:
            print(f"[TTS] Trying fallback voice: {VOICE_MAP['en']}")
            communicate = edge_tts.Communicate(
                text=str(text), 
                voice=VOICE_MAP["en"], 
                pitch='+7Hz', 
                rate='+13%'
            )
            await communicate.save(temp_path)
            
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                print("[TTS] Fallback voice successful")
                return temp_path
            else:
                raise Exception("Fallback voice also failed to create audio file")
                
        except Exception as fallback_e:
            print(f"Fallback also failed: {fallback_e}")
            cleanup_temp_file(temp_path)
            raise Exception(f"Both primary and fallback TTS failed: {e}, {fallback_e}")

def TTS(text, func=lambda r=None: True, lang="en"):
    """Improved TTS function with proper resource management"""
    if not text or not str(text).strip():
        print("[TTS] No text provided")
        return False
    
    # Thread-safe audio operations
    with audio_lock:
        temp_audio_path = None
        
        try:
            print(f"[TTS] Starting TTS for: {str(text)[:50]}...")
            
            # Initialize pygame if needed
            if not init_pygame():
                print("[TTS] Failed to initialize audio system")
                return False
            
            # Generate audio file
            try:
                # Create new event loop for this thread if needed
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        raise RuntimeError("Event loop is closed")
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                temp_audio_path = loop.run_until_complete(TextToAudioFile(text, lang=lang))
                
            except Exception as e:
                print(f"[TTS] Error generating audio: {e}")
                return False
            
            if not temp_audio_path or not os.path.exists(temp_audio_path):
                print("[TTS] No audio file generated")
                return False

            # Stop any currently playing audio
            try:
                pygame.mixer.music.stop()
                time.sleep(0.1)  # Small delay to ensure stop completes
            except Exception as e:
                print(f"[TTS] Error stopping previous audio: {e}")
            
            # Load and play new audio
            try:
                pygame.mixer.music.load(temp_audio_path)
                pygame.mixer.music.play()
                print("[TTS] Audio playback started")
                
            except Exception as e:
                print(f"[TTS] Error loading/playing audio: {e}")
                return False

            # Wait for playback to complete
            playback_timeout = 0
            max_playback_time = 300  # 30 seconds max
            
            while pygame.mixer.music.get_busy() and playback_timeout < max_playback_time:
                # Check if we should stop (func returns False)
                try:
                    if func() == False:
                        print("[TTS] Playback interrupted by function")
                        pygame.mixer.music.stop()
                        break
                except:
                    pass  # Continue if func() fails
                
                time.sleep(0.1)
                playback_timeout += 1

            if playback_timeout >= max_playback_time:
                print("[TTS] Playback timeout reached")
                pygame.mixer.music.stop()

            print("[TTS] Audio playback completed")
            return True

        except Exception as e:
            print(f"[TTS] Error in TTS function: {e}")
            return False
            
        finally:
            # Cleanup
            try:
                if pygame_initialized:
                    pygame.mixer.music.stop()
                
                if temp_audio_path:
                    # Small delay before cleanup to ensure pygame is done with file
                    time.sleep(0.2)
                    cleanup_temp_file(temp_audio_path)
                    
            except Exception as cleanup_e:
                print(f"[TTS] Error during cleanup: {cleanup_e}")

def TextToSpeech(text, func=lambda r=None: True, lang="en"):
    """Main TTS function with smart text truncation"""
    if not text:
        print("[TTS] No text provided to TextToSpeech")
        return False
        
    text_str = str(text).strip()
    if not text_str:
        print("[TTS] Empty text provided to TextToSpeech")
        return False
        
    print(f"[TTS] Processing text ({len(text_str)} chars): {text_str[:100]}...")
    
    # Split text into sentences
    data = text_str.split(".")
    data = [sentence.strip() for sentence in data if sentence.strip()]
    
    # Responses for long text
    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information.",
    ]

    # Truncate long responses for TTS
    if len(data) > 4 and len(text_str) >= 250:
        # Take first two sentences and add notification
        short_sentences = data[:2]
        short_text = ". ".join(short_sentences)
        if short_text and not short_text.endswith('.'):
            short_text += "."
        short_text += " " + random.choice(responses)
        
        print(f"[TTS] Text truncated for speech. Speaking: {short_text[:100]}...")
        return TTS(short_text, func, lang=lang)
    else:
        print("[TTS] Speaking full text")
        return TTS(text_str, func, lang=lang)

# Helper function to detect language from text
def detect_language_safely(text):
    """Safely detect language with fallback"""
    try:
        return detect(text)
    except:
        return "en"  # Default to English

# Test function for standalone testing
def test_tts():
    """Test function for TTS"""
    test_texts = [
        "Hello, this is a test of the text to speech system.",
        "This is a longer text to test the truncation feature. " * 20,
        "नमस्ते, यह एक परीक्षण है।",
        "Bonjour, c'est un test."
    ]
    
    for i, text in enumerate(test_texts):
        print(f"\n=== Test {i+1} ===")
        lang = detect_language_safely(text)
        print(f"Detected language: {lang}")
        
        success = TextToSpeech(text, lang=lang)
        print(f"TTS Result: {'Success' if success else 'Failed'}")
        
        if i < len(test_texts) - 1:
            time.sleep(1)  # Pause between tests

# Example main execution
if __name__ == "__main__":
    print("Text-to-Speech Test Mode")
    print("Options:")
    print("1. Enter 'test' for automated testing")
    print("2. Enter text to speak")
    print("3. Enter 'quit' to exit")
    
    try:
        while True:
            user_input = input("\nEnter text or command: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() == 'quit':
                break
            elif user_input.lower() == 'test':
                test_tts()
            else:
                try:
                    detected_lang = detect_language_safely(user_input)
                    print(f"Detected language: {detected_lang}")
                    
                    success = TextToSpeech(user_input, lang=detected_lang)
                    print(f"TTS Result: {'Success' if success else 'Failed'}")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        print("Cleaning up...")
        cleanup_all_temp_files()
        print("Cleanup completed.")