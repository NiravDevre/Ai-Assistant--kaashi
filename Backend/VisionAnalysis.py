import os
import requests
import base64
from PIL import Image
import pytesseract
import cv2
import numpy as np
from dotenv import get_key
import fitz  # PyMuPDF
import docx
import pandas as pd
from io import BytesIO
import json
from groq import Groq
import traceback

# Free OCR setup (you'll need to install Tesseract)
# Download from: https://github.com/tesseract-ocr/tesseract
# For Windows: https://github.com/UB-Mannheim/tesseract/wiki

# Load API keys
GROQ_API_KEY = get_key(".env", "GroqAPIKey")
HUGGINGFACE_API_KEY = get_key(".env", "HUGGINGFACE_API_KEY")

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

class VisionAnalyzer:
    def __init__(self):
        self.supported_image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        self.supported_file_formats = ['.pdf', '.docx', '.txt', '.csv', '.xlsx']
        
    def analyze_image(self, image_path, question="What do you see in this image?"):
        """
        Analyze image using multiple free methods:
        1. OCR for text extraction
        2. Hugging Face Vision models (free tier)
        3. Groq LLM for analysis of extracted data
        """
        try:
            if not os.path.exists(image_path):
                return "Image file not found."
            
            # Method 1: Extract text using OCR
            ocr_text = self._extract_text_from_image(image_path)
            
            # Method 2: Basic image analysis using OpenCV
            image_stats = self._analyze_image_properties(image_path)
            
            # Method 3: Try Hugging Face Vision API (free tier)
            hf_description = self._analyze_with_huggingface(image_path)
            
            # Combine all information and analyze with Groq
            combined_info = f"""
            Image Analysis Results:
            
            OCR Text Found: {ocr_text if ocr_text else 'No text detected'}
            
            Image Properties: {image_stats}
            
            Visual Description: {hf_description}
            
            User Question: {question}
            """
            
            # Use Groq to provide intelligent analysis
            final_analysis = self._analyze_with_groq(combined_info, question)
            
            return final_analysis
            
        except Exception as e:
            traceback.print_exc()
            return f"Error analyzing image: {str(e)}"
    
    def _extract_text_from_image(self, image_path):
        """Extract text using Tesseract OCR (free)"""
        try:
            # Load and preprocess image for better OCR
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Enhance image for better OCR results
            gray = cv2.medianBlur(gray, 3)
            gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Extract text
            text = pytesseract.image_to_string(gray, config='--psm 6')
            return text.strip()
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def _analyze_image_properties(self, image_path):
        """Basic image analysis using OpenCV"""
        try:
            image = cv2.imread(image_path)
            height, width, channels = image.shape
            
            # Calculate average colors
            avg_color = np.mean(image, axis=(0, 1))
            
            # Detect edges to understand complexity
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_count = np.count_nonzero(edges)
            
            return {
                "dimensions": f"{width}x{height}",
                "channels": channels,
                "average_colors": {
                    "blue": int(avg_color[0]),
                    "green": int(avg_color[1]),
                    "red": int(avg_color[2])
                },
                "complexity": "high" if edge_count > (width * height * 0.1) else "low",
                "file_size_kb": round(os.path.getsize(image_path) / 1024, 2)
            }
            
        except Exception as e:
            return f"Could not analyze image properties: {e}"
    
    def _analyze_with_huggingface(self, image_path):
        """Use Hugging Face's free vision models"""
        try:
            if not HUGGINGFACE_API_KEY:
                return "Hugging Face API key not found"
            
            # Using BLIP model for image captioning (free)
            API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
            headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
            
            with open(image_path, "rb") as f:
                data = f.read()
            
            response = requests.post(API_URL, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('generated_text', 'No description generated')
                return str(result)
            else:
                return f"HF API Error: {response.status_code}"
                
        except Exception as e:
            return f"Hugging Face analysis failed: {e}"
    
    def _analyze_with_groq(self, combined_info, user_question):
        """Use Groq to provide intelligent analysis of extracted information"""
        try:
            system_prompt = """You are an expert image and document analyzer. 
            Based on the provided information about an image (OCR text, visual properties, and descriptions), 
            provide a comprehensive and helpful response to the user's question.
            
            Be specific and detailed. If text was found, explain what it says. 
            If visual elements are described, incorporate that into your analysis.
            Always be helpful and try to answer the specific question asked."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{combined_info}\n\nPlease analyze this information and answer: {user_question}"}
            ]
            
            completion = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                max_tokens=1024,
                temperature=0.3
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            return f"Analysis with Groq failed: {e}"

class FileAnalyzer:
    def __init__(self):
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        
    def analyze_file(self, file_path, question="What is this file about?"):
        """Analyze different file types"""
        try:
            if not os.path.exists(file_path):
                return "File not found."
            
            file_ext = os.path.splitext(file_path.lower())[1]
            
            if file_ext == '.pdf':
                content = self._extract_pdf_content(file_path)
            elif file_ext == '.docx':
                content = self._extract_docx_content(file_path)
            elif file_ext == '.txt':
                content = self._extract_text_content(file_path)
            elif file_ext in ['.csv', '.xlsx']:
                content = self._extract_spreadsheet_content(file_path)
            else:
                return f"Unsupported file format: {file_ext}"
            
            # Analyze content with Groq
            return self._analyze_content_with_groq(content, question, file_ext)
            
        except Exception as e:
            traceback.print_exc()
            return f"Error analyzing file: {str(e)}"
    
    def _extract_pdf_content(self, file_path):
        """Extract text from PDF using PyMuPDF (free)"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text[:10000]  # Limit to first 10k characters
        except Exception as e:
            return f"Error reading PDF: {e}"
    
    def _extract_docx_content(self, file_path):
        """Extract text from DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text[:10000]  # Limit to first 10k characters
        except Exception as e:
            return f"Error reading DOCX: {e}"
    
    def _extract_text_content(self, file_path):
        """Extract content from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()[:10000]  # Limit to first 10k characters
        except Exception as e:
            return f"Error reading text file: {e}"
    
    def _extract_spreadsheet_content(self, file_path):
        """Extract content from CSV or Excel files"""
        try:
            if file_path.lower().endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Get basic info about the spreadsheet
            info = {
                "shape": df.shape,
                "columns": list(df.columns),
                "sample_data": df.head().to_dict(),
                "data_types": df.dtypes.to_dict()
            }
            
            return f"Spreadsheet Analysis:\n{json.dumps(info, indent=2, default=str)}"
            
        except Exception as e:
            return f"Error reading spreadsheet: {e}"
    
    def _analyze_content_with_groq(self, content, question, file_type):
        """Analyze extracted content using Groq"""
        try:
            system_prompt = f"""You are an expert document analyzer. 
            You have been given the content of a {file_type} file. 
            Analyze this content thoroughly and provide a helpful response to the user's question.
            
            Be specific about what you find in the document. 
            Summarize key points, extract important information, and directly answer the user's question."""
            
            # Truncate content if too long
            if len(content) > 8000:
                content = content[:8000] + "\n...[Content truncated]"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Document Content:\n{content}\n\nQuestion: {question}"}
            ]
            
            completion = self.groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=messages,
                max_tokens=1024,
                temperature=0.3
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            return f"Content analysis failed: {e}"

# Main functions for integration
def analyze_image(image_path, question="What do you see in this image?"):
    """Main function to analyze images"""
    analyzer = VisionAnalyzer()
    return analyzer.analyze_image(image_path, question)

def analyze_file(file_path, question="What is this file about?"):
    """Main function to analyze files"""
    analyzer = FileAnalyzer()
    return analyzer.analyze_file(file_path, question)

def analyze_media(file_path, question=None):
    """Universal function to analyze any supported file"""
    if not os.path.exists(file_path):
        return "File not found."
    
    file_ext = os.path.splitext(file_path.lower())[1]
    
    # Determine file type and use appropriate analyzer
    if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
        default_question = "What do you see in this image? Describe it in detail."
        return analyze_image(file_path, question or default_question)
    elif file_ext in ['.pdf', '.docx', '.txt', '.csv', '.xlsx']:
        default_question = "What is this document about? Summarize its key contents."
        return analyze_file(file_path, question or default_question)
    else:
        return f"Unsupported file format: {file_ext}"

# Test function
if __name__ == "__main__":
    # Test with an image
    image_path = input("Enter image path: ")
    if os.path.exists(image_path):
        result = analyze_image(image_path, "What text can you see in this image?")
        print("Image Analysis Result:")
        print(result)
    
    # Test with a document
    file_path = input("Enter document path: ")
    if os.path.exists(file_path):
        result = analyze_file(file_path, "Summarize this document")
        print("\nDocument Analysis Result:")
        print(result)