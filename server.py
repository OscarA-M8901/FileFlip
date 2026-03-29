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

@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml')

@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

@app.route('/ads.txt')
def ads_txt():
    return app.send_static_file('ads.txt')

@app.route('/blog')
def blog():
    return app.send_static_file('blog/index.html')

@app.route('/blog/<article>')
def blog_article(article):
    return app.send_static_file(f'blog/{article}.html')

@app.route('/favicon.ico')
def favicon_ico():
    return app.send_static_file('favicon.ico')

@app.route('/favicon.png')
def favicon_png():
    return app.send_static_file('favicon.png')

@app.route('/privacy')
def privacy():
    return app.send_static_file('privacy.html')

@app.route('/about')
def about():
    return app.send_static_file('about.html')

# Individual conversion pages
conversion_pages = [
    'jpg-to-png', 'png-to-jpg', 'pdf-to-docx', 'docx-to-pdf',
    'pdf-to-jpg', 'heic-to-jpg', 'image-to-pdf', 'mp4-to-mp3',
    'mov-to-mp4', 'image-resizer', 'webp-to-jpg', 'png-to-pdf',
    'mp4-to-gif', 'gif-to-mp4'
]

@app.route('/<page_slug>')
def conversion_page(page_slug):
    if page_slug in conversion_pages:
        return app.send_static_file(f'{page_slug}.html')
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
        return send_file(out_path, as_attachment=True, download_name=Path(file.filename).stem + out_ext)
    except Exception as e:
        return jsonify({'error': f'Image conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── IMAGE TO PDF ────────────────────────────────────────────────────────────
@app.route('/convert/image-to-pdf', methods=['POST'])
def image_to_pdf():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.heic']:
        return jsonify({'error': 'Please upload a JPG, PNG or WEBP image.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.pdf')
    try:
        img = Image.open(input_path).convert('RGB')
        img.save(out_path, 'PDF', resolution=100)
        out_name = Path(file.filename).stem + '.pdf'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'Image to PDF failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── HEIC TO JPG ─────────────────────────────────────────────────────────────
@app.route('/convert/heic-to-jpg', methods=['POST'])
def heic_to_jpg():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.heic', '.heif']:
        return jsonify({'error': 'Please upload a HEIC or HEIF file.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.jpg')
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        img = Image.open(input_path).convert('RGB')
        img.save(out_path, 'JPEG', quality=92)
        out_name = Path(file.filename).stem + '.jpg'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'HEIC conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── MOV TO MP4 ──────────────────────────────────────────────────────────────
@app.route('/convert/mov-to-mp4', methods=['POST'])
def mov_to_mp4():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.mov', '.avi', '.mkv', '.webm', '.flv']:
        return jsonify({'error': 'Please upload a MOV, AVI, MKV or WEBM file.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.mp4')
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', input_path, '-vcodec', 'h264', '-acodec', 'aac', '-y', out_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': 'Video conversion failed.'}), 500
        out_name = Path(file.filename).stem + '.mp4'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a shorter video.'}), 500
    except Exception as e:
        return jsonify({'error': f'Video conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── IMAGE RESIZER ───────────────────────────────────────────────────────────
@app.route('/convert/resize', methods=['POST'])
def resize_image():
    file = request.files.get('file')
    width = request.form.get('width', type=int)
    height = request.form.get('height', type=int)
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    if not width and not height:
        return jsonify({'error': 'Please provide a width or height.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        return jsonify({'error': 'Please upload a JPG, PNG or WEBP image.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    try:
        img = Image.open(input_path)
        orig_w, orig_h = img.size
        if width and not height:
            height = int(orig_h * width / orig_w)
        elif height and not width:
            width = int(orig_w * height / orig_h)
        img = img.resize((width, height), Image.LANCZOS)
        fmt = 'JPEG' if ext in ['.jpg', '.jpeg'] else ext[1:].upper()
        img.save(out_path, fmt, quality=92)
        out_name = Path(file.filename).stem + f'_{width}x{height}' + ext
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'Resize failed: {str(e)}'}), 500
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
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    try:
        if ext == '.pdf':
            from pdf2docx import Converter
            out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.docx')
            cv = Converter(input_path)
            cv.convert(out_path, start=0, end=None)
            cv.close()
            out_name = Path(file.filename).stem + '.docx'
        else:
            out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.pdf')
            result = subprocess.run(
                ['soffice', '--headless', '--convert-to', 'pdf',
                 '--outdir', UPLOAD_FOLDER, input_path],
                capture_output=True, text=True, timeout=120,
                env={**os.environ, 'HOME': '/tmp', 'TMPDIR': '/tmp'}
            )
            expected = os.path.join(UPLOAD_FOLDER, Path(input_path).stem + '.pdf')
            if result.returncode != 0 or not os.path.exists(expected):
                return jsonify({'error': 'DOCX to PDF conversion failed.'}), 500
            out_path = expected
            out_name = Path(file.filename).stem + '.pdf'
        if not os.path.exists(out_path):
            return jsonify({'error': 'Conversion failed — output file not found.'}), 500
        return send_file(out_path, as_attachment=True, download_name=out_name)
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
            return send_file(pages[0], as_attachment=True, download_name=Path(file.filename).stem + '.jpg')
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
            ['ffmpeg', '-i', input_path, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', '-y', out_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': 'Audio extraction failed. Make sure your video has an audio track.'}), 500
        return send_file(out_path, as_attachment=True, download_name=Path(file.filename).stem + '.mp3')
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a shorter video.'}), 500
    except Exception as e:
        return jsonify({'error': f'Audio extraction failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)


# ── WEBP TO JPG ─────────────────────────────────────────────────────────────
@app.route('/convert/webp-to-jpg', methods=['POST'])
def webp_to_jpg():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.webp', '.png', '.gif']:
        return jsonify({'error': 'Please upload a WEBP, PNG or GIF file.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.jpg')
    try:
        img = Image.open(input_path).convert('RGB')
        img.save(out_path, 'JPEG', quality=92)
        out_name = Path(file.filename).stem + '.jpg'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── PNG TO PDF ───────────────────────────────────────────────────────────────
@app.route('/convert/png-to-pdf', methods=['POST'])
def png_to_pdf():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.png', '.jpg', '.jpeg', '.webp']:
        return jsonify({'error': 'Please upload a PNG, JPG or WEBP file.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.pdf')
    try:
        img = Image.open(input_path).convert('RGB')
        img.save(out_path, 'PDF', resolution=100)
        out_name = Path(file.filename).stem + '.pdf'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── MP4 TO GIF ───────────────────────────────────────────────────────────────
@app.route('/convert/mp4-to-gif', methods=['POST'])
def mp4_to_gif():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return jsonify({'error': 'Please upload a video file (MP4, MOV, AVI, MKV).'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}{ext}')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.gif')
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', input_path, '-vf', 'fps=10,scale=480:-1:flags=lanczos',
             '-loop', '0', '-y', out_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': 'MP4 to GIF conversion failed.'}), 500
        out_name = Path(file.filename).stem + '.gif'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a shorter video (under 30 seconds).'}), 500
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
    finally:
        _cleanup(input_path)

# ── GIF TO MP4 ───────────────────────────────────────────────────────────────
@app.route('/convert/gif-to-mp4', methods=['POST'])
def gif_to_mp4():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file uploaded.'}), 400
    ext = Path(file.filename).suffix.lower()
    if ext != '.gif':
        return jsonify({'error': 'Please upload a GIF file.'}), 400
    input_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.gif')
    file.save(input_path)
    out_path = os.path.join(UPLOAD_FOLDER, f'{uuid.uuid4()}.mp4')
    try:
        result = subprocess.run(
            ['ffmpeg', '-i', input_path, '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
             '-vcodec', 'h264', '-acodec', 'aac', '-movflags', '+faststart', '-y', out_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or not os.path.exists(out_path):
            return jsonify({'error': 'GIF to MP4 conversion failed.'}), 500
        out_name = Path(file.filename).stem + '.mp4'
        return send_file(out_path, as_attachment=True, download_name=out_name)
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Conversion timed out. Try a smaller GIF.'}), 500
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500
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
