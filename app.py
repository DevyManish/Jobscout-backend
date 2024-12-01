from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import requests
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch API key from environment variables
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    logger.error("API_KEY environment variable is not set.")
    raise EnvironmentError("API_KEY environment variable is required.")

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in reader.pages])
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError("Failed to extract text from PDF. Ensure the file is a valid PDF.")

# Function to extract text from DOCX
def extract_text_from_docx(docx_file):
    try:
        doc = Document(docx_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        raise ValueError("Failed to extract text from DOCX. Ensure the file is a valid DOCX.")

# Function to rephrase text using external API
def rephrase_text(text):
    custom_prompt = f"""
    Please rephrase the following text according to ATS standards, including quantifiable measures and improvements where possible. The title should be 'Rephrased Text:' followed by the output.
    Original Text: {text}
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": custom_prompt}]}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        rephrased_text = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"rephrased_text": rephrased_text}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in API request: {e}")
        return {"error": "Error in API request."}

# Function to analyze resume with job description
def analyze_documents(resume_text, job_description):
    custom_prompt = f"""
    Analyze the following resume against the job description provided. Match hard and soft skills accurately, following ATS standards. Provide:
    - Match percentage of resume to job description.
    - List of missing keywords.
    - Overall analysis of resume's match with job description.
    - Recommendations to improve the resume with examples.
    Job Description: {job_description}
    Resume: {resume_text}
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": custom_prompt}]}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        analysis_text = response_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"analysis": analysis_text}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in API request: {e}")
        return {"error": "Error in API request."}

@app.route('/rephrase', methods=['POST'])
def rephrase():
    data = request.json
    text_to_rephrase = data.get('text')
    if text_to_rephrase:
        rephrased = rephrase_text(text_to_rephrase)
        return jsonify(rephrased)
    return jsonify({"error": "No text provided to rephrase."}), 400

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'job_description' not in request.form or 'file' not in request.files:
        return jsonify({"error": "Job description or resume file is missing."}), 400
    job_description = request.form['job_description']
    uploaded_file = request.files['file']
    file_type = os.path.splitext(uploaded_file.filename)[1].lower()
    try:
        if file_type == '.pdf':
            resume_text = extract_text_from_pdf(uploaded_file)
        elif file_type == '.docx':
            resume_text = extract_text_from_docx(uploaded_file)
        else:
            return jsonify({"error": "Unsupported file type. Only .pdf and .docx are allowed."}), 400
        analysis = analyze_documents(resume_text, job_description)
        return jsonify(analysis)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    """
    Health endpoint to check server status.
    Returns:
        JSON with server status.
    """
    return jsonify({"status": "OK"}), 200

if __name__ == '__main__':
    app.run(debug=True)
