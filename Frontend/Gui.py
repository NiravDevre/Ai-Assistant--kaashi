from PyQt5.QtWidgets import QApplication,QDesktopWidget, QMainWindow, QTextEdit,QHBoxLayout, QStackedWidget, QWidget, QLineEdit, QGridLayout, QVBoxLayout, QPushButton, QFrame, QLabel, QSizePolicy, QFileDialog
from PyQt5.QtGui import QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont, QPixmap, QTextBlockFormat,QTextCursor
from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSignal
from dotenv import dotenv_values
import sys
import os
from PyQt5.QtGui import QPalette, QColor


import sys
import os
import json
import traceback
from config import Username, TOKEN_FILE
from PyQt5.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt
import pyrebase
from firebaseConfig import firebaseConfig

firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()
db = firebase.database()

from config import TOKEN_FILE 

QApplication.setCursorFlashTime(1000) 

env_vars = dotenv_values(".env")
Assistantname = env_vars.get("Assistantname")
current_dir = os.getcwd()
old_chat_message = ""
TempDirPath = rf"{current_dir}\Frontend\Files"
GraphicsDirPath = rf"{current_dir}\Frontend\Graphics"

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer


def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + '?'
        else:
            new_query += '?'
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + '.'
        else:
            new_query += '.'

    return new_query.capitalize()


def SetMicrophoneStatus(Command):
    with open(rf"{TempDirPath}\Mic.data", "w", encoding="utf-8") as file:
        file.write(Command)


def GetMicrophoneStatus():
    with open(rf"{TempDirPath}\Mic.data", "r", encoding="utf-8") as file:
        Status = file.read()
    return Status


def SetAssistantStatus(Status):
    with open(rf"{TempDirPath}\Status.data", "w", encoding="utf-8") as file:
        file.write(Status)


def GetAssistantStatus():
    with open(rf"{TempDirPath}\Status.data", "r", encoding="utf-8") as file:
        Status = file.read()
    return Status

def MicButtonInitialized():
    SetMicrophoneStatus("True")


def MicButtonClosed():
    SetMicrophoneStatus("false")


def GraphicsDirectoryPath(Filename):
    Path = rf"{GraphicsDirPath}\{Filename}"
    return Path


def TempDirectoryPath(Filename):
    Path = rf"{TempDirPath}\{Filename}"
    return Path


def ShowTextToScreen(Text):
    with open(rf"{TempDirPath}\Responses.data", "w", encoding="utf-8") as file:
        file.write(Text)

# class LoginWindow(QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("Login to Kashi AI")
#         self.setGeometry(600, 300, 420, 280)

#         # ---------- UI ----------
#         root = QVBoxLayout()
#         root.setContentsMargins(16, 16, 16, 16)
#         root.setSpacing(8)

#         self.email_label = QLabel("Email")
#         self.email_input = QLineEdit()
#         self.email_input.setPlaceholderText("email@example.com")

#         self.password_label = QLabel("Password")
#         self.password_input = QLineEdit()
#         self.password_input.setEchoMode(QLineEdit.Password)
#         self.password_input.setPlaceholderText("••••••••")

#         self.username_label = QLabel("Username (for sign up)")
#         self.username_input = QLineEdit()
#         self.username_input.setPlaceholderText("Your display name")

#         # Remember me
#         remember_row = QHBoxLayout()
#         self.remember_check = QCheckBox("Remember me")
#         remember_row.addWidget(self.remember_check)
#         remember_row.addStretch()

#         # Buttons
#         btn_row = QHBoxLayout()
#         self.login_button = QPushButton("Login")
#         self.signup_button = QPushButton("Sign Up")
#         btn_row.addWidget(self.login_button)
#         btn_row.addWidget(self.signup_button)

#         for w in [
#             self.email_label, self.email_input,
#             self.password_label, self.password_input,
#             self.username_label, self.username_input,
#         ]:
#             root.addWidget(w)
#         root.addLayout(remember_row)
#         root.addLayout(btn_row)
#         self.setLayout(root)

#         # Events
#         self.login_button.clicked.connect(self.login)
#         self.signup_button.clicked.connect(self.signup)
#         self.password_input.returnPressed.connect(self.login)  # Enter to login

#         # Try auto-login if token exists
#         self.try_auto_login()

#     # ---------- Helpers ----------
#     def save_token(self, user_obj: dict):
#         try:
#             with open(TOKEN_FILE, "w", encoding="utf-8") as f:
#                 json.dump(user_obj, f)
#         except Exception:
#             traceback.print_exc()

#     def load_token(self):
#         if not os.path.exists(TOKEN_FILE):
#             return None
#         try:
#             with open(TOKEN_FILE, "r", encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception:
#             traceback.print_exc()
#             return None

#     def clear_token(self):
#         try:
#             if os.path.exists(TOKEN_FILE):
#                 os.remove(TOKEN_FILE)
#         except Exception:
#             traceback.print_exc()

#     def set_username_and_close(self, username: str):
#         import config
#         config.Username = username
#         QMessageBox.information(self, "Welcome", f"Welcome, {username}!")
#         self.close()

#     # ---------- Auto-login ----------
#     def try_auto_login(self):
#         token = self.load_token()
#         if not token:
#             return
#         try:
#             refreshed = auth.refresh(token["refreshToken"])
#             uid = refreshed["userId"]

#             # Update tokens
#             token.update(refreshed)
#             self.save_token(token)

#             username = db.child("users").child(uid).child("username").get(refreshed['idToken']).val()
#             if username:
#                 self.set_username_and_close(username)
#         except Exception:
#             pass  # Ignore and keep login window open

#     # ---------- Actions ----------
#     def login(self):
#         email = self.email_input.text().strip()
#         password = self.password_input.text().strip()
#         if not email or not password:
#             QMessageBox.warning(self, "Missing info", "Please enter both email and password.")
#             return

#         try:
#             user = auth.sign_in_with_email_and_password(email, password)
#             uid = user["localId"]

#             if self.remember_check.isChecked():
#                 self.save_token(user)
#             else:
#                 self.clear_token()

#             username = db.child("users").child(uid).child("username").get(user['idToken']).val()
#             if username:
#                 self.set_username_and_close(username)
#             else:
#                 QMessageBox.warning(self, "No username", "Username not found. Please sign up again.")

#         except Exception as e:
#             err_msg = str(e)
#             if "INVALID_PASSWORD" in err_msg:
#                 QMessageBox.warning(self, "Login failed", "Invalid password. Please try again.")
#             elif "EMAIL_NOT_FOUND" in err_msg or "USER_NOT_FOUND" in err_msg:
#                 QMessageBox.warning(self, "Login failed", "No account found with this email.")
#             elif "PERMISSION_DENIED" in err_msg:
#                 QMessageBox.warning(self, "Database error", "Permission denied. Check Firebase Realtime DB rules.")
#             else:
#                 traceback.print_exc()
#                 QMessageBox.warning(self, "Login failed", err_msg)

#     def signup(self):
#         email = self.email_input.text().strip()
#         password = self.password_input.text().strip()
#         username = self.username_input.text().strip()

#         if not email or not password or not username:
#             QMessageBox.warning(self, "Missing info", "Email, password, and username are required.")
#             return
#         if len(password) < 6:
#             QMessageBox.warning(self, "Weak password", "Password must be at least 6 characters.")
#             return

#         try:
#             user = auth.create_user_with_email_and_password(email, password)
#             uid = user["localId"]

#             db.child("users").child(uid).set({
#                 "email": email,
#                 "username": username
#             }, user['idToken'])

#             if self.remember_check.isChecked():
#                 self.save_token(user)
#             else:
#                 self.clear_token()

#             self.set_username_and_close(username)

#         except Exception as e:
#             err_msg = str(e)
#             if "EMAIL_EXISTS" in err_msg:
#                 QMessageBox.warning(self, "Signup failed", "This email is already registered. Please log in instead.")
#             elif "WEAK_PASSWORD" in err_msg:
#                 QMessageBox.warning(self, "Signup failed", "Password too weak. Must be at least 6 characters.")
#             elif "PERMISSION_DENIED" in err_msg:
#                 QMessageBox.warning(self, "Signup failed", "Permission denied. Check Firebase Realtime DB rules.")
#             else:
#                 traceback.print_exc()
#                 QMessageBox.warning(self, "Signup failed", err_msg)


class ChatSection(QWidget):
    def __init__(self, get_chatlog_func=None, save_chatlog_func=None):
        super(ChatSection, self).__init__()
        self.get_user_chatlog = get_chatlog_func
        self.save_user_chatlog = save_chatlog_func
        self.setAcceptDrops(True)
        # ... rest of your init code stays the same
        layout = QVBoxLayout(self)
        layout.setContentsMargins(-10, 40, 40, 100)
        layout.setSpacing(-100)
        self.chat_text_edit = QTextEdit()
        self.chat_text_edit.setReadOnly(True)
        self.chat_text_edit.setTextInteractionFlags(Qt.NoTextInteraction)  # No text interaction
        self.chat_text_edit.setFrameStyle(QFrame.NoFrame)
        layout.addWidget(self.chat_text_edit)

        self.setStyleSheet("background-color: black;")
        layout.setSizeConstraint(QVBoxLayout.SetDefaultConstraint)
        layout.setStretch(1, 1)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))

        text_color = QColor(Qt.blue)
        text_color_text = QTextCharFormat()
        text_color_text.setForeground(text_color)
        self.chat_text_edit.setCurrentCharFormat(text_color_text)

        button_style = ("""
            QPushButton {
                background-color: grey;
                color: white;
                border-radius: 10px;
                padding: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
        """)
        
        # --- Clear Last Chat button ---
        self.clear_chat = QPushButton("Clear Last Chat")
        self.clear_chat.setFixedWidth(150)
        self.clear_chat.setStyleSheet(button_style)
        self.clear_chat.clicked.connect(self.clear_last_chat)

        self.clear_all_btn = QPushButton("Clear All Chat")
        self.clear_all_btn.setFixedWidth(150)
        self.clear_all_btn.setStyleSheet(button_style)
        self.clear_all_btn.clicked.connect(self.clear_chat_screen)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.setFixedWidth(150)
        self.logout_btn.setStyleSheet(button_style)
        self.logout_btn.clicked.connect(self.logout_and_restart)

        # File analysis button
        self.analyze_file_btn = QPushButton("📁 Analyze File")
        self.analyze_file_btn.setFixedWidth(150)
        self.analyze_file_btn.setStyleSheet(button_style)
        self.analyze_file_btn.clicked.connect(self.select_and_analyze_file)


        btn_row = QHBoxLayout()
        btn_row.addWidget(self.clear_chat)
        btn_row.addWidget(self.clear_all_btn)
        btn_row.addWidget(self.analyze_file_btn)
        btn_row.addWidget(self.logout_btn)
        btn_row.setAlignment(Qt.AlignLeft)

        layout.addLayout(btn_row)

        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none;")
        movie = QMovie(GraphicsDirectoryPath("Kaashi.gif"))

        max_gif_size_w = 480
        max_gif_size_h = 270
        movie.setScaledSize(QSize(max_gif_size_w, max_gif_size_h))
        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        self.gif_label.setMovie(movie)
        movie.start()

        layout.addWidget(self.gif_label)

        self.label = QLabel()
        self.label.setStyleSheet("color: white; font-size:16px; margin-right: 195px; border: none; margin-top: -30px;")
        self.label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.label)
        layout.setSpacing(10)

            # Input box
        self.text_input = QLineEdit()
        self.text_input.setFixedWidth(750)

        # style via palette instead of caret-color
        palette = self.text_input.palette()
        palette.setColor(QPalette.Text, QColor("white"))       # text
        palette.setColor(QPalette.Base, QColor("#1b1c1c"))        # background
        palette.setColor(QPalette.Highlight, QColor("#555"))   # selection bg
        palette.setColor(QPalette.HighlightedText, QColor("white"))  # selection text
        self.text_input.setPalette(palette)

        self.text_input.setStyleSheet("""
            QLineEdit {
                font-size: 20px;
                height: 60px;
                padding: 10px 10px;
                background-color: #202121;
                border-top-left-radius: 30px;
                border-bottom-left-radius: 30px;
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border: none;
            }
        """)  
        self.text_input.setPlaceholderText("Type your message here...")
        self.text_input.setFocusPolicy(Qt.StrongFocus)
        self.text_input.setFocus()        

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFixedWidth(100)
        self.send_button.setFlat(True)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: none;
                height: 60px;
                font-size: 20px;
                padding: 10px 15px;
                border-top-right-radius: 30px;
                border-bottom-right-radius: 30px;
                border-top-left-radius: 0px;
                border-bottom-left-radius: 0px;
                color: black;
            }
            QPushButton:hover {
                background-color: grey;
            }
        """)

        # Layout row (no gap at all)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(0)   # no gap
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(self.send_button)
        input_layout.setAlignment(Qt.AlignCenter)

        layout.addLayout(input_layout)
        self.send_button.clicked.connect(self.handle_text_input)    # send on click
        self.text_input.returnPressed.connect(self.handle_text_input) 



        font = QFont()
        font.setPointSize(13)
        self.chat_text_edit.setFont(font)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.LoadMessages)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(5)

        self.chat_text_edit.viewport().installEventFilter(self)

        self.setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: black;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }

            QScrollBar::handle:vertical {
                background: white;
                min-height: 20px;
            }

            QScrollBar::add-line:vertical {
                background: black;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                height: 10px;
            }

            QScrollBar::sub-line:vertical {
                background: black;
                subcontrol-position: top;
                subcontrol-origin: margin;
                height: 10px;
            }
                           
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                border: none;
                background: none;
                color: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

        """
        )

    def logout_and_restart(self):
        import config
        
        # Clear token
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        
        # Reset global config
        config.Username = None
        config.FirebaseUID = None
        config.FirebaseToken = None
        
        # Close current window
        main_win = self.window()
        main_win.close()
        
        # Start new login process
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from Frontend.LoginScreen import LoginWindow
        login_window = LoginWindow()
        
        def on_new_login(username, uid, token):
            config.Username = username
            config.FirebaseUID = uid
            config.FirebaseToken = token
            
            # Restart main application
            from main import InitialExecution, SecondThread
            import threading
            
            InitialExecution(username)
            
            # Start voice thread
            from main import FirstThread
            voice_thread = threading.Thread(target=FirstThread, daemon=True)
            voice_thread.start()
            
            # Start query monitor
            from main import monitor_user_query
            query_thread = threading.Thread(target=monitor_user_query, daemon=True) 
            query_thread.start()
            
            # Show new GUI
            SecondThread()
        
        login_window.login_success.connect(on_new_login)
        login_window.show()

    def select_and_analyze_file(self):
        """Open file dialog and analyze selected file"""
        file_dialog = QFileDialog()
        file_dialog.setWindowTitle("Select Image or Document to Analyze")
        
        # Set file filters
        file_dialog.setNameFilters([
            "Images (*.jpg *.jpeg *.png *.bmp *.tiff *.webp)",
            "Documents (*.pdf *.docx *.txt *.csv *.xlsx)",
            "All Files (*.*)"
        ])
        
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                
                # Ask user what they want to know about the file
                from PyQt5.QtWidgets import QInputDialog
                question, ok = QInputDialog.getText(
                    self, 
                    'Analysis Question', 
                    'What would you like to know about this file?\n(Leave empty for general analysis):',
                    text="What do you see in this file?"
                )
                
                if ok:
                    # Create the analysis command
                    if any(file_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']):
                        command = f"analyze image {file_path}"
                    else:
                        command = f"analyze file {file_path}"
                    
                    if question.strip():
                        command += f" {question.strip()}"
                    
                    # Add to text input and process
                    self.text_input.setText(command)
                    self.handle_text_input()

    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle file drop event"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]  # Take the first file
            
            # Check if it's a supported file type
            supported_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', 
                                '.pdf', '.docx', '.txt', '.csv', '.xlsx']
            
            if any(file_path.lower().endswith(ext) for ext in supported_extensions):
                # Ask what to analyze
                from PyQt5.QtWidgets import QInputDialog
                question, ok = QInputDialog.getText(
                    self, 
                    'Quick Analysis', 
                    f'Dropped: {os.path.basename(file_path)}\n\nWhat would you like to know?',
                    text="Analyze this file"
                )
                
                if ok:
                    command = f"analyze {'image' if any(file_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']) else 'file'} {file_path}"
                    if question.strip():
                        command += f" {question.strip()}"
                    
                    self.text_input.setText(command)
                    self.handle_text_input()
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Unsupported File", 
                                f"File type not supported.\n\nSupported: Images (jpg, png, etc.) and Documents (pdf, docx, txt, csv, xlsx)")

    def LoadMessages(self):
        global old_chat_message

        with open(TempDirectoryPath('Responses.data'), "r", encoding='utf-8') as file:
            messages = file.read()

            if None == messages:
                pass

            elif len(messages) <= 1:
                pass

            elif str(old_chat_message) == str(messages):
                pass

            else:
                self.addMessage(message=messages,color="White")
                old_chat_message = messages
    
    def clear_chat_screen(self):
        self.chat_text_edit.clear()
        try:
            with open(TempDirectoryPath("Responses.data"), "w", encoding="utf-8") as f:
                f.write("")  # empty it
        except Exception as e:
            print("[!] Could not clear Responses.data:", e)

    def clear_last_chat(self):
        cursor = self.chat_text_edit.textCursor()

        # Move cursor to the end
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)  # select last block (last chat line)

        # Remove it
        cursor.removeSelectedText()
        cursor.deletePreviousChar()  # remove newline


    def SpeechRecogText(self):
        with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
            messages = file.read()
            self.label.setText(messages)

    def load_icon(self, path, width=60, height=60):
        pixmap = QPixmap(path)
        new_pixmap = pixmap.scaled(width, height)
        self.icon_label.setPixmap(new_pixmap)

    def toggle_icon(self, event=None):
        if self.toggled:
            self.load_icon(GraphicsDirectoryPath('voice.png'), 60, 60)
            MicButtonInitialized()
        else:
            self.load_icon(GraphicsDirectoryPath('mic.png'), 60, 60)
            MicButtonClosed()

        self.toggled = not self.toggled 

    def handle_text_input(self):
        query = self.text_input.text().strip()
        if query:
            self.text_input.clear()
            
            # Save user query only if functions are available
            if self.get_user_chatlog and self.save_user_chatlog:
                messages = self.get_user_chatlog()
                messages.append({"role": "user", "content": query})
                self.save_user_chatlog(messages)
            
            # Write to file for processing
            with open(TempDirectoryPath("UserQuery.data"), "w", encoding="utf-8") as f:
                f.write(query)

    def addMessage(self, message, color):
        cursor = self.chat_text_edit.textCursor()
        format = QTextCharFormat()
        formatm = QTextBlockFormat()
        formatm.setTopMargin(10)
        formatm.setLeftMargin(10)
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.setBlockFormat(formatm)
        cursor.insertText(message + "\n")
        self.chat_text_edit.setTextCursor(cursor)

class InitialScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Fullscreen GIF
        gif_label = QLabel(self)
        movie = QMovie(GraphicsDirectoryPath('Kaashi.gif'))
        movie.setScaledSize(QSize(screen_width, screen_height))  # Fit full screen
        gif_label.setMovie(movie)
        gif_label.setAlignment(Qt.AlignCenter)
        movie.start()

        content_layout.addWidget(gif_label)

        # Optional status label (speech text)
        self.label = QLabel("")
        self.label.setStyleSheet("color: white; font-size: 16px; margin: 0; background-color: rgba(0,0,0,0%);")
        self.label.setAlignment(Qt.AlignCenter)

        content_layout.addWidget(self.label)
        self.setLayout(content_layout)
        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)
        self.setStyleSheet("background-color: black;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.SpeechRecogText)
        self.timer.start(5)

    def SpeechRecogText(self):
        with open(TempDirectoryPath('Status.data'), "r", encoding='utf-8') as file:
            messages = file.read()
            self.label.setText(messages)

class MessageScreen(QWidget):
    def __init__(self, get_chatlog_func=None, save_chatlog_func=None, parent=None):
        super().__init__(parent)
        desktop = QApplication.desktop()
        screen_width = desktop.screenGeometry().width()
        screen_height = desktop.screenGeometry().height()
        
        layout = QVBoxLayout()
        
        label = QLabel("")
        layout.addWidget(label)
        
        chat_section = ChatSection(get_chatlog_func, save_chatlog_func)
        layout.addWidget(chat_section)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: black;")
        self.setFixedHeight(screen_height)
        self.setFixedWidth(screen_width)

class ImagePreviewScreen(QWidget):
    show_image_signal = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(-10, 40, 40, 100)
        layout.setAlignment(Qt.AlignCenter) 
        self.img_label = QLabel("No image generated yet")
        self.img_label.setStyleSheet("color: white; font-size: 18px; background-color: #222;border: none;border-radius: 10px;")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(400, 400)  # thumbnail style
        self.img_label.setScaledContents(True) #

        self.download_btn = QPushButton("Download Image")
        self.download_btn.setFixedWidth(150) 
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                border: none;
                height: 40px;
                font-size: 16px;
                padding: 5px 15px;
                border-radius: 10px;
                color: black;
            }
            QPushButton:hover {
                background-color: grey;
            }
        """)
        # --- Group image + button together ---
        img_block = QVBoxLayout()
        img_block.setAlignment(Qt.AlignCenter)
        img_block.setSpacing(10)  # spacing between image & button
        img_block.addWidget(self.img_label, alignment=Qt.AlignCenter)
        img_block.addWidget(self.download_btn, alignment=Qt.AlignHCenter)
    
        layout.addLayout(img_block)

        self.last_image_path = None
        # connect signal to function
        self.show_image_signal.connect(self.show_image)

    def show_image(self, path):
        pixmap = QPixmap(path)
        # scale the image to fit inside 400x400, keeping aspect ratio
        pixmap = pixmap.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_label.setPixmap(pixmap)
        self.last_image_path = path


    def download_image(self):
        if self.last_image_path:
            from PyQt5.QtWidgets import QFileDialog
            import shutil
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "generated.png", "Images (*.png *.jpg)")
            if save_path:
                shutil.copy(self.last_image_path, save_path)

class CustomTopBar(QWidget):
    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        self.initUI()
        self.current_screen = None
        self.stacked_widget = stacked_widget

    def initUI(self):
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: black;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        hover_style = """
            QPushButton {
                background-color: "black";
                border: none;
                height: 50px;
                width: 60px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            """
        close_hover_style = """
            QPushButton {
                background-color: "black";
                border: none;
                height: 50px;
                width: 60px;
            }
            QPushButton:hover {
                background-color: red;
            }
            """
        hoverbtn_style = """
            QPushButton {
                background-color: white;
                border: none;
                height: 40px;
                color = black;
                padding: 5px 15px;
                border-radius:10px;
            }
            QPushButton:hover {
                background-color: grey;
            }
            """

        title_label = QLabel(f"  {str(Assistantname).capitalize()} AI  ")
        title_label.setStyleSheet("color: white; font-size: 18px; background-color: black ; font-family:display")
      
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 0, 0, 0)
        center_layout.setAlignment(Qt.AlignCenter)
        center_widget.setStyleSheet("background-color:black")
            
        home_button = QPushButton(" Home")
        home_button.setIcon(QIcon(GraphicsDirectoryPath("Home.png")))
        home_button.setFlat(True)
        home_button.setStyleSheet(hoverbtn_style)
        
        message_button = QPushButton(" Chat")
        message_button.setIcon(QIcon(GraphicsDirectoryPath("Chats.png")))
        message_button.setFlat(True)
        message_button.setStyleSheet(hoverbtn_style)

        image_button = QPushButton(" Images")
        image_button.setIcon(QIcon(GraphicsDirectoryPath("Image.png")))  # make sure you have an icon
        image_button.setFlat(True)
        image_button.setStyleSheet(hoverbtn_style)
        image_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))

        minimize_button = QPushButton()
        minimize_icon = QIcon(GraphicsDirectoryPath("Minimize.svg"))
        minimize_button.setIcon(minimize_icon)
        minimize_button.setFlat(True)
        minimize_button.setStyleSheet(hover_style)
        minimize_button.clicked.connect(self.minimizeWindow)

        self.maximize_button = QPushButton()
        self.maximize_icon = QIcon(GraphicsDirectoryPath("Maximize.svg"))
        self.restore_icon = QIcon(GraphicsDirectoryPath("Maximize.svg"))
        self.maximize_button.setIcon(self.maximize_icon)
        self.maximize_button.setFlat(True)
        self.maximize_button.setStyleSheet(hover_style)
        self.maximize_button.clicked.connect(self.maximizeWindow)

        close_button = QPushButton()
        close_icon = QIcon(GraphicsDirectoryPath("Close.svg"))
        close_button.setIcon(close_icon)
        close_button.setFlat(True)
        close_button.setStyleSheet(close_hover_style)
        close_button.clicked.connect(self.closeWindow)

        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setFrameShape(QFrame.HLine)
        line_frame.setFrameShadow(QFrame.Sunken)
        line_frame.setStyleSheet("border-color: black;")

        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))

        center_layout.addWidget(home_button)
        center_layout.addWidget(message_button)
        center_layout.addWidget(image_button)

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(center_widget)
        layout.addStretch()
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)
        self.draggable = True
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("black"))
        super().paintEvent(event)

    def minimizeWindow(self):
        self.parent().showMinimized()

    def maximizeWindow(self):
        if self.parent().isMaximized():
            self.parent().showNormal()
            self.maximize_button.setIcon(self.maximize_icon)
        else:
            self.parent().showMaximized()
            self.maximize_button.setIcon(self.restore_icon)

    def closeWindow(self):
        self.parent().close()

    def mousePressEvent(self, event):
        if self.draggable:
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.draggable and self.offset:
            new_pos = event.globalPos() - self.offset
            self.parent().move(new_pos)

    def showMessageScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()

        message_screen = MessageScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(message_screen)
        self.current_screen = message_screen

    def showInitialScreen(self):
        if self.current_screen is not None:
            self.current_screen.hide()

        initial_screen = InitialScreen(self)
        layout = self.parent().layout()
        if layout is not None:
            layout.addWidget(initial_screen)
        self.current_screen = initial_screen

class MainWindow(QMainWindow):
    def __init__(self, get_chatlog_func=None, save_chatlog_func=None):
        super().__init__()
        self.get_chatlog_func = get_chatlog_func
        self.save_chatlog_func = save_chatlog_func
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.initUI()

    def initUI(self):
        screen_rect = QDesktopWidget().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()
        stacked_widget = QStackedWidget(self)
        initial_screen = InitialScreen()
        message_screen = MessageScreen(self.get_chatlog_func, self.save_chatlog_func)
        stacked_widget.addWidget(initial_screen)
        stacked_widget.addWidget(message_screen)
        image_preview_screen = ImagePreviewScreen()
        stacked_widget.addWidget(image_preview_screen)

        # Keep reference
        self.image_preview_screen = image_preview_screen
        self.stacked_widget = stacked_widget

        self.setGeometry(0, 0, screen_width, screen_height)
        self.setStyleSheet("background-color: black;")
        top_bar = CustomTopBar(self, stacked_widget)
        self.setMenuWidget(top_bar)
        self.setCentralWidget(stacked_widget)
        global MainWindowInstance
        MainWindowInstance = self

# Global reference for MainWindow instance (used by ImageGenration.py)
MainWindowInstance = None

def GraphicalUserInterface(get_chatlog_func=None, save_chatlog_func=None):
    # Don't create a new QApplication if one already exists
    # app = QApplication.instance()
    # if app is None:
    #     app = QApplication(sys.argv)
    
    window = MainWindow(get_chatlog_func, save_chatlog_func)
    # window.show()
    
    # # Only start event loop if this is the main entry point
    # if __name__ == "__main__":
    #     sys.exit(app.exec_())
    
    return window  # Return window so it can be stored

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
