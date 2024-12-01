from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from docx import Document
import os
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

API_KEY = os.getenv("API_KEY")  # Store your API key in environment variables or .env

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

# Function to extract text from DOCX
def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Function to rephrase text using external API
def rephrase_text(text):
    custom_prompt = f"""
    Please rephrase the following text according to ATS standards, including quantifiable measures and improvements where possible, also maintain precise and concise points which will pass ATS screening:
    The title should be Rephrased Text:, and then display the output.
    Original Text: {text}
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [
            {"role": "user", "parts": [{"text": custom_prompt}]}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        response_json = response.json()
        if "candidates" in response_json:
            rephrased_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            return {"rephrased_text": rephrased_text}
        else:
            return {"error": "Rephrased text not found in the response."}
    else:
        return {"error": "Error in API request."}

# Function to analyze resume with job description
def analyze_documents(resume_text, job_description):
    custom_prompt = f"""
    Please analyze the following resume in the context of the job description provided. Strictly check every single line in job description and analyze my resume whether there is a match exactly. Strictly maintain high ATS standards and give scores only to the correct ones. Focus on hard skills which are missing and also soft skills which are missing. Provide the following details.:
    1. The match percentage of the resume to the job description. Display this.
    2. A list of missing keywords accurate ones.
    3. Final thoughts on the resume's overall match with the job description in 3 lines.
    4. Recommendations on how to add the missing keywords and improve the resume in 3-4 points with examples.
    Please display in the above order don't mention the numbers like 1. 2. etc and strictly follow ATS standards so that analysis will be accurate. Strictly follow the above templates omg. don't keep changing every time.
    Strictly follow the above things and template which has to be displayed and don't keep changing again and again. Don't fucking change the template from above.
    Title should be Resume analysis and maintain the same title for all. Also if someone uploads the same unchanged resume twice, keep in mind to give the same results. Display new ones only if they have changed their resume according to your suggestions or at least few changes.
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
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        response_json = response.json()
        if "candidates" in response_json:
            full_response = response_json["candidates"][0]["content"]["parts"][0]["text"]
            
            try:
                match_percentage = full_response.split("Match percentage of the resume to the job description: ")[1].split("\n")[0]
                suggestions_start = full_response.find("Recommendations on how to add the missing keywords and improve the resume:")
                suggestions = full_response[suggestions_start:]
                return {
                    "match_percentage": match_percentage,
                    "suggestions": suggestions
                }
            except (IndexError, AttributeError):
                return {"error": "Failed to parse response. Please check the API output format."}
        else:
            return {"error": "Analysis response not found."}
    else:
        return {"error": f"Error in API request. Status code: {response.status_code}"}
@app.route('/rephrase', methods=['POST'])
def rephrase():
    data = request.json
    text_to_rephrase = data.get('text', None)
    if text_to_rephrase:
        rephrased = rephrase_text(text_to_rephrase)
        return jsonify(rephrased)
    else:
        return jsonify({"error": "No text provided to rephrase."}), 400

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'job_description' not in request.form or 'file' not in request.files:
        return jsonify({"error": "Job description or resume file is missing."}), 400
    job_description = request.form['job_description']
    uploaded_file = request.files['file']   
    file_type = os.path.splitext(uploaded_file.filename)[1].lower()
    if file_type == '.pdf':
        resume_text = extract_text_from_pdf(uploaded_file)
    elif file_type == '.docx':
        resume_text = extract_text_from_docx(uploaded_file)
    else:
        return jsonify({"error": "Unsupported file type. Only .pdf and .docx are allowed."}), 400
    analysis = analyze_documents(resume_text, job_description)
    return jsonify(analysis)

if __name__ == '__main__':
    app.run(debug=True)
