import os
import uuid
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
import boto3
import google.generativeai as genai
from langchain.prompts import PromptTemplate
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text_processor")

# AWS Configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)
bucket_name = os.getenv("S3_BUCKET_NAME")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'txt'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# LangChain Prompt Template
SUMMARY_PROMPT = PromptTemplate.from_template(
    """Please provide a detailed summary of the following text. 
    Focus on key points, main ideas, and important details. 
    The summary should be comprehensive yet concise.

    Text: {text}

    Detailed Summary:"""
)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def upload_to_s3(file_path, object_name):
    try:
        with open(file_path, 'rb') as file_data:
            s3_client.upload_fileobj(file_data, bucket_name, object_name)
        logger.info(f"File {object_name} uploaded to S3 successfully")
        return True
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        return False

def generate_summary(text):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = SUMMARY_PROMPT.format(text=text)
        response = model.generate_content(prompt)
        
        if response and hasattr(response, 'text'):
            return response.text.strip()
        return "Error: No summary generated"
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return f"Error: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'})
    
    if file and allowed_file(file.filename):
        try:
            # Save file locally
            filename = secure_filename(file.filename)
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_path)
            
            # Upload to S3 with unique name
            s3_filename = f"text-{uuid.uuid4()}.txt"
            upload_to_s3(local_path, s3_filename)
            
            # Read file content
            with open(local_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Generate summary
            summary = generate_summary(text_content)
            
            return jsonify({
                'status': 'success',
                'filename': filename,
                'content': text_content,
                'summary': summary
            })
            
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    return jsonify({'status': 'error', 'message': 'Invalid file type'})

if __name__ == '__main__':
    app.run(debug=True)