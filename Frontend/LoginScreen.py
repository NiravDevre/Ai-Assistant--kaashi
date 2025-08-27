import sys
import os
import json
import traceback
import config
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QCheckBox, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal
import pyrebase
from firebaseConfig import firebaseConfig
from cryptography.fernet import Fernet

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

KEY_FILE = "key.key"
TOKEN_FILE = config.TOKEN_FILE

# -------- Encryption Helpers --------
def load_or_create_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    else:
        with open(KEY_FILE, "rb") as f:
            key = f.read()
    return Fernet(key)

fernet = load_or_create_key()

class LoginWindow(QWidget):
    login_success = pyqtSignal(str, str, str)  # username, uid, token
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login to Kashi AI")
        self.setGeometry(600, 300, 420, 320)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        
        # Initialize UI
        self.setup_ui()
        self.is_signup_mode = False
        
        # Try auto-login first
        self.try_auto_login()

    def setup_ui(self):
        """Setup the user interface"""
        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        # Email field
        self.email_label = QLabel("Email")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")

        # Password field with show/hide button
        self.password_label = QLabel("Password")
        pw_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("••••••••")

        self.show_pw_button = QPushButton("👁")
        self.show_pw_button.setCheckable(True)
        self.show_pw_button.setFixedWidth(40)
        self.show_pw_button.clicked.connect(self.toggle_password)

        pw_row.addWidget(self.password_input)
        pw_row.addWidget(self.show_pw_button)

        # Username field (hidden by default)
        self.username_label = QLabel("Username (for sign up)")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Your display name")
        self.username_label.hide()
        self.username_input.hide()

        # Remember me checkbox
        remember_row = QHBoxLayout()
        self.remember_check = QCheckBox("Remember me")
        remember_row.addWidget(self.remember_check)
        remember_row.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.signup_button = QPushButton("Sign Up")
        btn_row.addWidget(self.login_button)
        btn_row.addWidget(self.signup_button)

        # Add all widgets to layout
        widgets = [
            self.email_label, self.email_input,
            self.password_label, pw_row,
            self.username_label, self.username_input,
            remember_row, btn_row
        ]
        
        for widget in widgets:
            if hasattr(widget, 'addLayout'):
                root.addLayout(widget)
            else:
                root.addWidget(widget)

        self.setLayout(root)
        
        # Connect events
        self.login_button.clicked.connect(self.handle_login_click)
        self.signup_button.clicked.connect(self.handle_signup_click)
        self.password_input.returnPressed.connect(self.handle_login_click)

    def toggle_password(self):
        """Toggle password visibility"""
        if self.show_pw_button.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    def handle_login_click(self):
        """Handle login button click"""
        if self.is_signup_mode:
            self.show_login_mode()
        else:
            self.login()

    def handle_signup_click(self):
        """Handle signup button click"""
        if self.is_signup_mode:
            self.signup()
        else:
            self.show_signup_mode()

    def show_login_mode(self):
        """Switch to login mode"""
        self.is_signup_mode = False
        self.username_label.hide()
        self.username_input.hide()
        self.login_button.setText("Login")
        self.signup_button.setText("Sign Up")

    def show_signup_mode(self):
        """Switch to signup mode"""
        self.is_signup_mode = True
        self.username_label.show()
        self.username_input.show()
        self.login_button.setText("Back to Login")
        self.signup_button.setText("Create Account")

    def save_token(self, user_obj: dict, email=None, password=None, username=None, uid=None, token=None):
        """Save authentication token with encryption"""
        try:
            data = user_obj.copy()
            if email:
                data["saved_email"] = email
            if password:
                data["saved_password"] = password
            if username:
                data["saved_username"] = username
            if uid:
                data["saved_uid"] = uid
            if token:
                data["saved_token"] = token

            # Encrypt and save
            raw = json.dumps(data).encode("utf-8")
            encrypted = fernet.encrypt(raw)

            with open(TOKEN_FILE, "wb") as f:
                f.write(encrypted)
                
            print(f"Token saved successfully for user: {username}")
        except Exception as e:
            print(f"Error saving token: {e}")
            traceback.print_exc()

    def load_token(self):
        """Load and decrypt authentication token"""
        if not os.path.exists(TOKEN_FILE):
            return None
        try:
            with open(TOKEN_FILE, "rb") as f:
                encrypted = f.read()
            raw = fernet.decrypt(encrypted)
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            print(f"Error loading token: {e}")
            return None

    def clear_token(self):
        """Remove saved token"""
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
                print("Token cleared successfully")
        except Exception as e:
            print(f"Error clearing token: {e}")

    def set_global_config(self, username: str, uid: str, token: str):
        """Set global configuration variables"""
        config.Username = username
        config.FirebaseUID = uid
        config.FirebaseToken = token
        print(f"Global config set - Username: {username}, UID: {uid}")

    def try_auto_login(self):
        """Attempt automatic login with saved token"""
        print("Attempting auto-login...")
        token = self.load_token()
        if not token:
            print("No saved token found")
            return False

        # Auto-fill fields if available
        if "saved_email" in token:
            self.email_input.setText(token["saved_email"])
        if "saved_password" in token:
            self.password_input.setText(token["saved_password"])
            self.remember_check.setChecked(True)
        if "saved_username" in token:
            self.username_input.setText(token["saved_username"])

        try:
            # Try to refresh the token
            if "refreshToken" not in token:
                print("No refresh token available")
                return False
                
            refreshed = auth.refresh(token["refreshToken"])
            uid = token.get("saved_uid") or token.get("userId") or token.get("localId")
            
            if not uid:
                print("No UID found in token")
                return False

            # Update token data
            token.update(refreshed)
            
            # Verify user exists in database
            username = db.child("users").child(uid).child("username").get(refreshed['idToken']).val()
            if not username:
                print("Username not found in database")
                return False

            # Save updated token
            self.save_token(token, 
                          token.get("saved_email"),
                          token.get("saved_password"), 
                          username, uid, refreshed['idToken'])

            # Set global config
            self.set_global_config(username, uid, refreshed['idToken'])
            
            print(f"Auto-login successful for user: {username}")
            
            # Emit success signal and close
            self.login_success.emit(username, uid, refreshed['idToken'])
            self.close()
            return True
            
        except Exception as e:
            print(f"Auto-login failed: {e}")
            # Clear invalid token
            self.clear_token()
            return False

    def login(self):
        """Handle user login"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Missing Information", "Please enter both email and password.")
            return

        try:
            print(f"Attempting login for: {email}")
            user = auth.sign_in_with_email_and_password(email, password)
            uid = user["localId"]
            token = user["idToken"]

            # Get username from database
            username = db.child("users").child(uid).child("username").get(token).val()
            if not username:
                QMessageBox.warning(self, "Login Error", "Username not found. Please sign up again.")
                return

            # Set global config
            self.set_global_config(username, uid, token)

            # Save token if remember me is checked
            if self.remember_check.isChecked():
                self.save_token(user, email, password, username, uid, token)
            else:
                self.clear_token()

            print(f"Login successful for user: {username}")
            QMessageBox.information(self, "Success", f"Welcome back, {username}!")
            
            # Emit success signal and close
            self.login_success.emit(username, uid, token)
            self.close()

        except Exception as e:
            error_msg = str(e)
            print(f"Login error: {error_msg}")
            
            if "INVALID_PASSWORD" in error_msg:
                QMessageBox.warning(self, "Login Failed", "Invalid password. Please try again.")
            elif "EMAIL_NOT_FOUND" in error_msg or "USER_NOT_FOUND" in error_msg:
                QMessageBox.warning(self, "Login Failed", "No account found with this email.")
            elif "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
                QMessageBox.warning(self, "Login Failed", "Too many failed attempts. Please try again later.")
            else:
                QMessageBox.warning(self, "Login Failed", f"Login error: {error_msg}")

    def signup(self):
        """Handle user signup"""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        username = self.username_input.text().strip()

        if not email or not password or not username:
            QMessageBox.warning(self, "Missing Information", "Please fill in all fields.")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "Weak Password", "Password must be at least 6 characters long.")
            return

        try:
            print(f"Attempting signup for: {email}")
            
            # Check if username is already taken
            existing = db.child("usernames").child(username).get().val()
            if existing:
                QMessageBox.warning(self, "Signup Failed", "Username already taken. Please choose another.")
                return

            # Create Firebase Auth account
            user = auth.create_user_with_email_and_password(email, password)
            uid = user["localId"]
            token = user["idToken"]

            # Save user data to database
            db.child("users").child(uid).set({
                "email": email,
                "username": username
            }, token)

            # Reserve username
            db.child("usernames").child(username).set({"uid": uid}, token)

            # Set global config
            self.set_global_config(username, uid, token)

            # Save token if remember me is checked
            if self.remember_check.isChecked():
                self.save_token(user, email, password, username, uid, token)
            else:
                self.clear_token()

            print(f"Signup successful for user: {username}")
            QMessageBox.information(self, "Success", f"Account created successfully! Welcome, {username}!")
            
            # Emit success signal and close
            self.login_success.emit(username, uid, token)
            self.close()

        except Exception as e:
            error_msg = str(e)
            print(f"Signup error: {error_msg}")
            
            if "EMAIL_EXISTS" in error_msg:
                QMessageBox.warning(self, "Signup Failed", "An account with this email already exists.")
            elif "WEAK_PASSWORD" in error_msg:
                QMessageBox.warning(self, "Signup Failed", "Password is too weak. Please use at least 6 characters.")
            else:
                QMessageBox.warning(self, "Signup Failed", f"Signup error: {error_msg}")

def has_valid_token():
    """
    Check if a valid token exists and return user info.
    Returns (username, uid, token) if valid, None otherwise.
    """
    try:
        window = LoginWindow()
        token = window.load_token()
        if not token or "refreshToken" not in token:
            return None

        # Try to refresh the token
        refreshed = auth.refresh(token["refreshToken"])
        uid = token.get("saved_uid") or token.get("userId") or token.get("localId")
        
        if not uid:
            return None

        # Verify username exists
        username = db.child("users").child(uid).child("username").get(refreshed['idToken']).val()
        if not username:
            return None

        # Update saved token
        token.update(refreshed)
        window.save_token(token, 
                         token.get("saved_email"),
                         token.get("saved_password"), 
                         username, uid, refreshed['idToken'])

        # Set global config
        config.Username = username
        config.FirebaseUID = uid
        config.FirebaseToken = refreshed['idToken']

        print(f"Valid token found for user: {username}")
        return username, uid, refreshed['idToken']

    except Exception as e:
        print(f"Token validation failed: {e}")
        return None