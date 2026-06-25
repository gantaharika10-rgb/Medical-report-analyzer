"""
Medical Report Analyzer - 100% Local, No External APIs
Uses: pytesseract (OCR), pdfplumber (PDF), scikit-learn (ML), deep-translator (translation)
"""

import os, json, uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from utils.extractor import extract_text_from_file
from utils.analyzer import analyze_report
from utils.translator import translate_text, SUPPORTED_LANGUAGES
from utils.sample_report import SAMPLE_TEXT

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
ALLOWED = {'png', 'jpg', 'jpeg', 'pdf', 'tiff', 'tif', 'bmp'}

os.makedirs('uploads', exist_ok=True)
os.makedirs('models', exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED


@app.route('/')
def index():
    return render_template('index.html', languages=SUPPORTED_LANGUAGES)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PNG, JPG, PDF, TIFF, BMP files allowed'}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        text, pages, method = extract_text_from_file(filepath)
        if not text.strip():
            return jsonify({'error': 'Could not extract text. Check the file has readable content.'}), 400

        analysis = analyze_report(text)
        lang_code = request.form.get('language', 'en')
        summary_translated = ''
        if lang_code != 'en':
            summary_translated = translate_text(analysis['summary'], lang_code)

        return jsonify({
            'success': True,
            'extracted_text': text[:3000],
            'pages': pages,
            'method': method,
            'analysis': analysis,
            'summary_translated': summary_translated,
            'language': lang_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        try:
            os.remove(filepath)
        except:
            pass


@app.route('/analyze-sample', methods=['POST'])
def analyze_sample():
    try:
        data = request.get_json()
        lang_code = data.get('language', 'en')
        analysis = analyze_report(SAMPLE_TEXT)
        summary_translated = ''
        if lang_code != 'en':
            summary_translated = translate_text(analysis['summary'], lang_code)
        return jsonify({
            'success': True,
            'extracted_text': SAMPLE_TEXT[:3000],
            'pages': 1,
            'method': 'Sample report',
            'analysis': analysis,
            'summary_translated': summary_translated,
            'language': lang_code
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/translate', methods=['POST'])
def translate():
    data = request.get_json()
    text = data.get('text', '')
    lang = data.get('language', 'en')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    try:
        result = translate_text(text, lang)
        return jsonify({'translated': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*55)
    print("  Medical Report Analyzer  -  100% Local")
    print("="*55)
    print("  No external APIs - Runs offline after setup")
    print("  Open: http://localhost:5000")
    print("="*55 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
