import os
import zipfile
import tempfile
from flask import Flask, render_template, request, send_file, flash, Response
from werkzeug.utils import secure_filename
from pdf2docx import Converter
from docx import Document
from PIL import Image
from moviepy.editor import VideoFileClip

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_file(filepath, conv_type, filename):
    ext = filename.rsplit('.', 1)[1].lower()
    base = filename.rsplit('.', 1)[0]
    result_files = []

    # PDF para DOCX
    if conv_type == "pdf2word" and ext == "pdf":
        docx_path = os.path.join(tempfile.gettempdir(), base + ".docx")
        try:
            cv = Converter(filepath)
            cv.convert(docx_path)
            cv.close()
            result_files.append(docx_path)
        except Exception as e:
            return None, f"Erro ao converter PDF para Word: {str(e)}"

    # DOCX para PDF
    elif conv_type == "word2pdf" and ext == "docx":
        pdf_path = os.path.join(tempfile.gettempdir(), base + ".pdf")
        try:
            # Usando docx2pdf não funciona em Linux/Render, então converte para imagem PDF
            doc = Document(filepath)
            txt = "\n".join([p.text for p in doc.paragraphs])
            img = Image.new('RGB', (1000, 1400), color='white')
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.text((50, 50), txt, fill='black')
            img.save(pdf_path, "PDF", resolution=100.0)
            result_files.append(pdf_path)
        except Exception as e:
            return None, f"Erro ao converter Word para PDF: {str(e)}"

    # Imagem para PDF
    elif conv_type == "img2pdf" and ext in ["jpg", "jpeg", "png"]:
        pdf_path = os.path.join(tempfile.gettempdir(), base + ".pdf")
        try:
            image = Image.open(filepath)
            image.save(pdf_path, "PDF", resolution=100.0)
            result_files.append(pdf_path)
        except Exception as e:
            return None, f"Erro ao converter Imagem para PDF: {str(e)}"

    # PDF para Imagem PNG
    elif conv_type == "pdf2img" and ext == "pdf":
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(filepath)
            img_paths = []
            for i, img in enumerate(images):
                img_path = os.path.join(tempfile.gettempdir(), f"{base}_page{i+1}.png")
                img.save(img_path, "PNG")
                img_paths.append(img_path)
            result_files.extend(img_paths)
        except Exception as e:
            return None, f"Erro ao converter PDF para Imagem: {str(e)}"

    # PNG para JPG
    elif conv_type == "png2jpg" and ext == "png":
        jpg_path = os.path.join(tempfile.gettempdir(), base + ".jpg")
        try:
            image = Image.open(filepath)
            rgb_im = image.convert('RGB')
            rgb_im.save(jpg_path, "JPEG")
            result_files.append(jpg_path)
        except Exception as e:
            return None, f"Erro ao converter PNG para JPG: {str(e)}"

    # JPG para PNG
    elif conv_type == "jpg2png" and ext in ["jpg", "jpeg"]:
        png_path = os.path.join(tempfile.gettempdir(), base + ".png")
        try:
            image = Image.open(filepath)
            image.save(png_path, "PNG")
            result_files.append(png_path)
        except Exception as e:
            return None, f"Erro ao converter JPG para PNG: {str(e)}"

    # Vídeo para MP3
    elif conv_type == "video2mp3" and ext in ["mp4", "mov", "avi"]:
        mp3_path = os.path.join(tempfile.gettempdir(), base + ".mp3")
        try:
            clip = VideoFileClip(filepath)
            clip.audio.write_audiofile(mp3_path)
            clip.close()
            result_files.append(mp3_path)
        except Exception as e:
            return None, f"Erro ao converter Vídeo para MP3: {str(e)}"
    else:
        return None, "Tipo de conversão ou arquivo inválido."

    return result_files, None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/convert", methods=["GET", "POST"])
def convert():
    if request.method == "POST":
        files = request.files.getlist("files")
        conv_type = request.form.get("conv_type")
        if not files or not conv_type:
            return Response("Selecione arquivos e tipo de conversão.", status=400)
        converted_files = []
        errors = []
        for file in files:
            if not allowed_file(file.filename):
                errors.append(f"Arquivo inválido: {file.filename}")
                continue
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            result, err = convert_file(filepath, conv_type, filename)
            if result:
                converted_files.extend(result)
            else:
                errors.append(f"{filename}: {err}")
            try:
                os.remove(filepath)
            except Exception:
                pass
        if converted_files and not errors:
            # Se só um arquivo, retorna direto
            if len(converted_files) == 1:
                return send_file(converted_files[0], as_attachment=True)
            # Se múltiplos, faz zip
            zip_path = os.path.join(tempfile.gettempdir(), "arquivos_convertidos.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for f in converted_files:
                    zipf.write(f, arcname=os.path.basename(f))
            for f in converted_files:
                try:
                    os.remove(f)
                except Exception:
                    pass
            return send_file(zip_path, as_attachment=True)
        else:
            return Response("Erros: " + " | ".join(errors), status=400)
    return render_template("convert.html")

@app.errorhandler(413)
def too_large(e):
    return "Arquivo muito grande!", 413

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))