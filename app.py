from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import json
import traceback
from datetime import datetime
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import base64
from io import BytesIO
from PIL import Image
import razorpay
import hmac
import hashlib
from datetime import datetime, timedelta

# Import your existing modules
try:
    from Backend.Model import FirstLayerDMM
    from Backend.RealTimeSearchEngine import RealtimeSearchEngine  
    from Backend.Chatbot import ChatBot
    from Backend.ImageGenration import generate_image
    from Backend.Memory import remember as remember_memory, forget as forget_memory, set_preference as set_pref
    from Backend.Automation import Automation
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure your Backend modules are in the correct path")

# Firebase imports
try:
    import pyrebase
    from firebaseConfig import firebaseConfig
    firebase = pyrebase.initialize_app(firebaseConfig)
    auth = firebase.auth()
    db = firebase.database()
    FIREBASE_AVAILABLE = True
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    FIREBASE_AVAILABLE = False

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_xxxxx")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "your_secret")

razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Global variables
executor = ThreadPoolExecutor(max_workers=4)
active_sessions = {}

class WebAppSession:
    def __init__(self, user_id, username=None):
        self.user_id = user_id
        self.username = username or f"User_{user_id}"
        self.chat_history = []
        self.preferences = {}
        self.memory_facts = []
        
    def add_message(self, role, content):
        self.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_chat_history(self):
        return self.chat_history

def get_session(user_id):
    if user_id not in active_sessions:
        active_sessions[user_id] = WebAppSession(user_id)
    return active_sessions[user_id]

def parse_decisions(decisions):
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
        
        AUTOMATION_FUNCS = {"open", "close", "play", "system", "content", "google search", "youtube search"}
        REALTIME_KEYWORDS = ["today", "current", "latest", "breaking", "recent", "now", "weather", "price", "score", "update"]

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
            buckets["general"].append(d)
    
    return buckets

async def process_automation(decisions):
    """Process automation tasks"""
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(Automation, decisions), 
            timeout=60
        )
        return "Automation completed successfully." if result else "Automation completed."
    except Exception as e:
        return f"Automation failed: {str(e)}"

async def process_realtime(queries):
    """Process real-time queries"""
    results = []
    for query in queries:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(RealtimeSearchEngine, query),
                timeout=60
            )
            results.append(result)
        except Exception as e:
            results.append(f"Real-time query failed: {str(e)}")
    return results

async def process_general(queries):
    """Process general chat queries"""
    results = []
    for query in queries:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(ChatBot, query),
                timeout=45
            )
            results.append(result)
        except Exception as e:
            results.append(f"General query failed: {str(e)}")
    return results

async def process_images(prompts):
    """Process image generation"""
    results = []
    for i, prompt in enumerate(prompts):
        try:
            path = await asyncio.wait_for(
                asyncio.to_thread(generate_image, prompt, i+1),
                timeout=90
            )
            if path:
                # Convert image to base64 for web display
                with open(path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                results.append({
                    "type": "image",
                    "data": f"data:image/png;base64,{img_data}",
                    "prompt": prompt
                })
            else:
                results.append(f"Image generation failed for: {prompt}")
        except Exception as e:
            results.append(f"Image generation error: {str(e)}")
    return results

@app.route('/')
def home():
    """Serve the main web interface"""
    # You can either serve the HTML file directly or render it as a template
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    """Main chat endpoint"""
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        session = get_session(user_id)
        session.add_message("user", message)
        
        # Get AI decisions
        try:
            decisions = FirstLayerDMM(message)
        except Exception as e:
            error_response = f"Sorry, I couldn't process that: {str(e)}"
            session.add_message("assistant", error_response)
            return jsonify({
                "response": error_response,
                "type": "error"
            })
        
        if not decisions:
            fallback_response = "I'm not sure how to help with that."
            session.add_message("assistant", fallback_response)
            return jsonify({
                "response": fallback_response,
                "type": "general"
            })
        
        # Parse decisions
        buckets = parse_decisions(decisions)
        
        if buckets["exit"]:
            farewell = "Goodbye! Thanks for chatting with me."
            session.add_message("assistant", farewell)
            return jsonify({
                "response": farewell,
                "type": "exit"
            })
        
        # Process tasks asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Process different types of tasks
            automation_result = None
            realtime_results = []
            general_results = []
            image_results = []
            
            if buckets["automation"]:
                automation_result = loop.run_until_complete(
                    process_automation(buckets["automation"])
                )
            
            if buckets["realtime"]:
                realtime_results = loop.run_until_complete(
                    process_realtime(buckets["realtime"])
                )
            
            if buckets["general"]:
                general_results = loop.run_until_complete(
                    process_general(buckets["general"])
                )
            
            if buckets["images"]:
                image_results = loop.run_until_complete(
                    process_images(buckets["images"])
                )
            
        finally:
            loop.close()
        
        # Combine results
        response_parts = []
        response_data = {}
        
        if realtime_results:
            response_parts.extend([str(r) for r in realtime_results if r])
        
        if general_results:
            response_parts.extend([str(r) for r in general_results if r])
        
        if automation_result:
            response_parts.append(str(automation_result))
        
        if image_results:
            response_data["images"] = image_results
            response_parts.append(f"Generated {len(image_results)} image(s)")
        
        final_response = "\n\n".join(response_parts) if response_parts else "Task completed."
        
        session.add_message("assistant", final_response)
        
        return jsonify({
            "response": final_response,
            "type": "success",
            "data": response_data
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"Server error: {str(e)}",
            "type": "error"
        }), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id', 'anonymous')
        question = request.form.get('question', 'Analyze this file')
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file temporarily
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        
        session = get_session(user_id)
        
        # Determine file type and create appropriate command
        if file.content_type.startswith('image/'):
            command = f"analyze image {file_path} {question}"
        else:
            command = f"analyze file {file_path} {question}"
        
        session.add_message("user", f"Uploaded: {file.filename} - {question}")
        
        # Process the analysis command
        try:
            decisions = FirstLayerDMM(command)
            # This would normally process through your existing analysis pipeline
            # For now, return a placeholder response
            response = f"I can see you've uploaded '{file.filename}'. In a full implementation, I would analyze this file and provide detailed insights based on your question: '{question}'"
            
        except Exception as e:
            response = f"Analysis failed: {str(e)}"
        
        session.add_message("assistant", response)
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
        return jsonify({
            "response": response,
            "type": "file_analysis"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"Upload error: {str(e)}",
            "type": "error"
        }), 500

@app.route('/api/create-order', methods=['POST'])
def create_order():
    """Create a Razorpay order for premium purchase"""
    try:
        data = request.json
        user_id = data.get("user_id")
        username = data.get("username", "Anonymous")
        amount = data.get("amount", 100000)  # ₹1000 in paise
        
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        # Generate unique receipt ID
        receipt_id = f"KASHI_PREMIUM_{user_id}_{int(datetime.now().timestamp())}"
        
        # Create order in Razorpay
        order_data = {
            "amount": amount,  # amount in paise
            "currency": "INR",
            "receipt": receipt_id,
            "notes": {
                "user_id": user_id,
                "username": username,
                "product": "Kashi AI Premium License",
                "description": "Lifetime access to premium features"
            }
        }
        
        order = razorpay_client.order.create(order_data)
        
        # Store order info temporarily (you might want to use a database)
        if 'pending_orders' not in globals():
            global pending_orders
            pending_orders = {}
            
        pending_orders[order['id']] = {
            "user_id": user_id,
            "username": username,
            "amount": amount,
            "receipt": receipt_id,
            "created_at": datetime.now().isoformat(),
            "status": "created"
        }
        
        app.logger.info(f"Created order {order['id']} for user {user_id}")
        
        return jsonify({
            "id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "receipt": order['receipt']
        })
        
    except Exception as e:
        app.logger.error(f"Order creation error: {str(e)}")
        return jsonify({
            "error": "Failed to create payment order",
            "message": str(e)
        }), 500

@app.route('/api/payment/verify', methods=['POST'])
def verify_payment():
    """Verify Razorpay payment and activate premium features"""
    try:
        data = request.json
        user_id = data.get("user_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_signature = data.get("razorpay_signature")
        
        if not all([user_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return jsonify({
                "success": False,
                "error": "Missing required payment parameters"
            }), 400
        
        # Verify signature
        generated_signature = hmac.new(
            key=RAZORPAY_KEY_SECRET.encode('utf-8'),
            msg=f"{razorpay_order_id}|{razorpay_payment_id}".encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(generated_signature, razorpay_signature):
            app.logger.warning(f"Invalid payment signature for user {user_id}")
            return jsonify({
                "success": False,
                "error": "Payment verification failed"
            }), 400
        
        # Fetch payment details from Razorpay
        try:
            payment_details = razorpay_client.payment.fetch(razorpay_payment_id)
            order_details = razorpay_client.order.fetch(razorpay_order_id)
        except Exception as e:
            app.logger.error(f"Failed to fetch payment details: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Unable to verify payment with gateway"
            }), 500
        
        # Check payment status
        if payment_details['status'] != 'captured':
            return jsonify({
                "success": False,
                "error": "Payment not completed"
            }), 400
        
        # Check if amounts match
        if payment_details['amount'] != order_details['amount']:
            app.logger.warning(f"Amount mismatch for payment {razorpay_payment_id}")
            return jsonify({
                "success": False,
                "error": "Payment amount verification failed"
            }), 400
        
        # Activate premium for user
        session = get_session(user_id)
        session.preferences["premium"] = True
        session.preferences["premium_activated_at"] = datetime.now().isoformat()
        session.preferences["payment_id"] = razorpay_payment_id
        session.preferences["order_id"] = razorpay_order_id
        
        # Store in database if using Firebase
        if FIREBASE_AVAILABLE:
            try:
                db.child("users").child(user_id).child("premium").set({
                    "status": True,
                    "activated_at": datetime.now().isoformat(),
                    "payment_id": razorpay_payment_id,
                    "order_id": razorpay_order_id,
                    "amount_paid": payment_details['amount'],
                    "plan": "lifetime"
                })
            except Exception as e:
                app.logger.warning(f"Failed to update Firebase: {str(e)}")
        
        # Clean up pending orders
        if 'pending_orders' in globals() and razorpay_order_id in pending_orders:
            pending_orders[razorpay_order_id]["status"] = "completed"
            pending_orders[razorpay_order_id]["completed_at"] = datetime.now().isoformat()
        
        app.logger.info(f"Premium activated for user {user_id}, payment {razorpay_payment_id}")
        
        return jsonify({
            "success": True,
            "message": "Premium features activated successfully!",
            "download_link": "/downloads/KashiAI_Premium_Setup.exe",
            "premium_features": [
                "AI Image Generation",
                "File Upload & Analysis", 
                "Advanced Voice Features",
                "Offline Mode",
                "Priority Support",
                "No Usage Limits",
                "Custom Integrations"
            ]
        })
        
    except Exception as e:
        app.logger.error(f"Payment verification error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Payment verification failed",
            "message": str(e)
        }), 500

@app.route('/api/premium/status/<user_id>')
def check_premium_status(user_id):
    """Check if user has premium access"""
    try:
        session = get_session(user_id)
        is_premium = session.preferences.get("premium", False)
        
        return jsonify({
            "is_premium": is_premium,
            "activated_at": session.preferences.get("premium_activated_at"),
            "features_available": [
                "AI Image Generation",
                "File Upload & Analysis",
                "Advanced Voice Features", 
                "Offline Mode",
                "Priority Support",
                "No Usage Limits"
            ] if is_premium else []
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "is_premium": False
        }), 500

@app.route('/api/track-download', methods=['POST'])
def track_download():
    """Track premium app downloads"""
    try:
        data = request.json
        user_id = data.get("user_id")
        action = data.get("action", "download")
        
        session = get_session(user_id)
        
        # Log download attempt
        if "downloads" not in session.preferences:
            session.preferences["downloads"] = []
            
        session.preferences["downloads"].append({
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "ip": request.remote_addr
        })
        
        app.logger.info(f"Download tracked for user {user_id}: {action}")
        
        return jsonify({"success": True})
        
    except Exception as e:
        app.logger.error(f"Download tracking error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory', methods=['POST'])
def memory_endpoint():
    """Handle memory operations"""
    try:
        data = request.json
        user_id = data.get('user_id', 'anonymous')
        operation = data.get('operation')  # 'remember', 'forget', 'set_preference'
        content = data.get('content', '')
        
        session = get_session(user_id)
        
        if operation == 'remember':
            result = remember_memory(content)
            response = f"I'll remember that: {content}" if result else "I already knew that."
            
        elif operation == 'forget':
            result = forget_memory(content)
            response = f"I've forgotten: {content}" if result else "I don't recall that information."
            
        elif operation == 'set_preference':
            key = data.get('key', '')
            value = data.get('value', '')
            result = set_pref(key, value)
            response = f"I've set your preference: {key} = {value}"
            
        else:
            return jsonify({"error": "Invalid operation"}), 400
        
        session.add_message("assistant", response)
        
        return jsonify({
            "response": response,
            "type": "memory"
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"Memory error: {str(e)}",
            "type": "error"
        }), 500

@app.route('/api/chat/history/<user_id>')
def get_chat_history(user_id):
    """Get chat history for a user"""
    try:
        session = get_session(user_id)
        return jsonify({
            "history": session.get_chat_history()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/clear/<user_id>', methods=['POST'])
def clear_chat_history(user_id):
    """Clear chat history for a user"""
    try:
        if user_id in active_sessions:
            active_sessions[user_id].chat_history = []
        return jsonify({"message": "Chat history cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def status():
    """API status endpoint"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "firebase_available": FIREBASE_AVAILABLE
    })

# Authentication endpoints (if using Firebase)
if FIREBASE_AVAILABLE:
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.json
            email = data.get('email')
            password = data.get('password')
            
            user = auth.sign_in_with_email_and_password(email, password)
            uid = user["localId"]
            
            # Get username from database
            username = db.child("users").child(uid).child("username").get(user['idToken']).val()
            
            return jsonify({
                "success": True,
                "user_id": uid,
                "username": username,
                "token": user['idToken']
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 401
    
    @app.route('/api/auth/signup', methods=['POST'])
    def signup():
        try:
            data = request.json
            email = data.get('email')
            password = data.get('password')
            username = data.get('username')
            
            user = auth.create_user_with_email_and_password(email, password)
            uid = user["localId"]
            
            # Save username to database
            db.child("users").child(uid).set({
                "email": email,
                "username": username
            }, user['idToken'])
            
            return jsonify({
                "success": True,
                "user_id": uid,
                "username": username,
                "token": user['idToken']
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 400

if __name__ == '__main__':
    # Create templates directory and save the HTML file
    pending_orders = {}

    if not RAZORPAY_KEY_ID or RAZORPAY_KEY_ID == "rzp_test_xxxxx":
        print("WARNING: Please set your actual Razorpay Key ID in environment variables")
        
    if not RAZORPAY_KEY_SECRET or RAZORPAY_KEY_SECRET == "your_secret":
        print("WARNING: Please set your actual Razorpay Key Secret in environment variables")
    print("Payment gateway configured with Razorpay")
    os.makedirs('templates', exist_ok=True)
    
    # You'll need to save the HTML content from the first artifact as templates/index.html
    
    print("Starting Kashi AI Web Server...")
    print("Make sure to:")
    print("1. Install required packages: pip install flask flask-cors")
    print("2. Save the HTML content as templates/index.html")
    print("3. Ensure your Backend modules are accessible")
    print("4. Configure your .env file with API keys")
    
    app.run(host='0.0.0.0', port=5000, debug=True)