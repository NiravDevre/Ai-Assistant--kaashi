# config.py - Fixed version with proper initialization
import os

# Global variables for user session
Username = None
FirebaseUID = None  
FirebaseToken = None

# File paths
TOKEN_FILE = "session_token.dat"

# Ensure data directories exist
if not os.path.exists("Data"):
    os.makedirs("Data")

if not os.path.exists("Frontend/Files"):
    os.makedirs("Frontend/Files", exist_ok=True)

# Initialize default status files
def initialize_status_files():
    """Initialize default status files if they don't exist"""
    files_dir = "Frontend/Files"
    
    default_files = {
        "Status.data": "Available...",
        "Mic.data": "False", 
        "Responses.data": "",
        "UserQuery.data": ""
    }
    
    for filename, default_content in default_files.items():
        filepath = os.path.join(files_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(default_content)

# Call initialization
initialize_status_files()