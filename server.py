from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
import tempfile
from pathlib import Path
from PIL import Image
import subprocess

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

UPLOAD_FOLDER = tempfile.mkdtemp()

@app.route('/')
def index():
    return app.send_static_file('index.html')

# ── IMAGE CONVERSION (JPG ↔ PNG) ───────────────────────────────────────────
@app.route('/convert/image', methods=['POST'])
def convert_image():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        return jsonify({'error': 'Please upload a JPG or PNG file.'}), 400

    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)

    try:
        img = Image.open(input_path)
        if ext in ['.jpg', '.jpeg']:
            out_ext = '.png'
            out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.png')
            img.convert('RGBA').save(out_path, 'PNG')
        else:
            out_ext = '.jpg'
            out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.jpg')
            img.convert('RGB').save(out_path, 'JPEG', quality=92)

        out_name = Path(file.filename).stem + out_ext
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'Image conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── DOCUMENT CONVERSION (PDF ↔ DOCX) ──────────────────────────────────────
@app.route('/convert/document', methods=['POST'])
def convert_document():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.pdf', '.docx']:
        return jsonify({'error': 'Please upload a PDF or DOCX file.'}), 400

    uid = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f'{uid}{ext}')
    file.save(input_path)

    out_ext = 'docx' if ext == '.pdf' else 'pdf'
    out_path = os.path.join(UPLOAD_FOLDER, f'{uid}.{out_ext}')

    try:
        result = subprocess.run(
            ['soffice', '--headless', '--convert-to', out_ext,
             '--outdir', UPLOAD_FOLDER, input_path],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, 'HOME': '/tmp', 'TMPDIR': '/tmp'}
        )

        app.logger.info(f"soffice stdout: {result.stdout}")
        app.logger.info(f"soffice stderr: {result.stderr}")

        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': f'Document conversion failed. {result.stderr[:200]}'}), 500

        out_name = Path(file.filename).stem + f'.{out_ext}'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a smaller file.'}), 500
    except Exception as e:
        return jsonify({'error': f'Document conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── PDF TO JPG ──────────────────────────────────────────────────────────────
@app.route('/convert/pdf-to-jpg', methods=['POST'])
def convert_pdf_to_jpg():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400

    ext = Path(file.filename).suffix.lower()
    if ext != '.pdf':
        return jsonify({'error': 'Please upload a PDF file.'}), 400

    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.pdf')
    file.save(input_path)
    out_prefix = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}_page')

    try:
        result = subprocess.run(
            ['pdftoppm', '-jpeg', '-r', '150', input_path, out_prefix],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            return jsonify({'error': 'PDF to image conversion failed.'}), 500

        import glob, zipfile, io
        pages = sorted(glob.glob(f'{out_prefix}*.jpg'))

        if not pages:
            return jsonify({'error': 'No pages found in PDF.'}), 500

        if len(pages) == 1:
            out_name = Path(file.filename).stem + '.jpg'
            return send_file(pages[0], as_attachment=True, download_name=out_name)

        zip_buffer = io.BytesIO()
        stem = Path(file.filename).stem
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for i, page_path in enumerate(pages, 1):
                zf.write(page_path, f'{stem}_page{i}.jpg')
        zip_buffer.seek(0)
        return send_file(zip_buffer, mimetype='application/zip',
                         as_attachment=True, download_name=stem + '_pages.zip')
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a smaller file.'}), 500
    except Exception as e:
        return jsonify({'error': f'PDF to image failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── MP4 TO MP3 ──────────────────────────────────────────────────────────────
@app.route('/convert/audio', methods=['POST'])
def convert_audio():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return jsonify({'error': 'Please upload a video file (MP4, MOV, AVI, MKV).'}), 400

    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.mp3')

    try:
        result = subprocess.run(
            ['ffmpeg', '-i', input_path, '-vn',
             '-acodec', 'libmp3lame', '-q:a', '2',
             '-y', out_path],
            capture_output=True, text=True, timeout=120
        )

        app.logger.info(f"ffmpeg stderr: {result.stderr[-500:]}")

        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': f'Audio extraction failed. Make sure your video has an audio track.'}), 500

        out_name = Path(file.filename).stem + '.mp3'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a shorter video.'}), 500
    except Exception as e:
        return jsonify({'error': f'Audio extraction failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
