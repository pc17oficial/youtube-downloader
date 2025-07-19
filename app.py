import base64
import os
import tempfile
import uuid
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
import yt_dlp

app = Flask(__name__)

# Conteúdo base64 dos cookies - usa exatamente o teu conteúdo.
COOKIES_BASE64 = """
IyBOZXRzY2FwZSBIVFRQIENvb2tpZSBGaWxlCiMgVGhpcyBmaWxlIGlzIGdl
bmVyYXRlZCBieSB5dC1kbHAuICBEbyBub3QgZWRpdC4KCnlvdXR1YmUuY29t
CVRSVUUJCS8JEEFMU0UJMAlQUkVGCGhsPWVuJnR6PVVUDQp5b3V0dWJlLmNv
bQlUUlVFCTAJVFJVRQkwCVNPQ1MJQ0FJCi55b3V0dWJlLmNvbQlUUlVFCTAJ
VFJVRQkwCVlTQwlCcFRud2NRd2l3NAoueW91dHViZS5jb20JVFJVRQkxNzY4
NDQwNzA4CV9fU2VjdXJlLVJPTExPVVQvVE9LRU4JQ1A3U3F2Ykc2NS1wMXdF
UXQ3eWtwdVBIaGdNWTdwdlBwdVBIaGdNJTNEDQp5b3V0dWJlLmNvbQlUUlVF
CTE3Njg0NDU0MjEJVklTSVRPUl9JTkZPMV9MSVZFCWNQdXc5Y2x2ejBjCi55
b3V0dWJlLmNvbQlUUlVFCTE3Njg0NDU0MjEJVklTSVRPUl9QUklWQUNZX01F
VEFEQVRBCUNnSlFWQkloRWgwU0d3c01EZzhRRVJJVEZCVVdGeGdaR2hzY0hS
NGZJQ0VpSXlRbEppQWYNCi55b3V0dWJlLmNvbQlUUlVFCTE4MTU5NjU0MjEJ
X19TZWN1cmUtWVRfVFZGQVMJdD00ODY5MTMmcj0yCi55b3V0dWJlLmNvbQlU
UlVFCTE3Njg0NDU0MjEJREVWSUNFX0lORk8JQ2h4T2VsVjVUMFJW
TlU5VVdUTk9SR013VG1wck5VNUVTVEpPUVQwOUVPMlA3TU1HR0lUcjY4TUcN
CnllLmNvbQlUUlVFCTE3NTI4OTQ3MzUJR1BTCTEKLnlvdXR1YmUuY29tCVRS
VUUJL3R2CVRSVUUJMTc4NTcyNTQyMQlfX1NlY3VyZS1ZVF9ERVJQCUNLQ3g1
SlUt
"""

# Decodificar e gravar cookies num ficheiro temporário
def write_cookies_file():
    decoded = base64.b64decode(COOKIES_BASE64.encode('utf-8'))
    tf = tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.txt')
    tf.write(decoded)
    tf.close()
    return tf.name

COOKIES_FILE = write_cookies_file()

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "URL em falta."}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "cookiefile": COOKIES_FILE,
        "nocheckcertificate": True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    try:
        formats = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info.get("formats", []):
                has_video = f.get("vcodec") != "none"
                has_audio = f.get("acodec") != "none"
                tipo = "[Vídeo + Áudio]" if has_video and has_audio else "[Vídeo]" if has_video else "[Áudio]"
                resolution = f.get("format_note") or (str(f.get("height")) + "p" if f.get("height") else "?")
                label = f"{tipo} - {resolution}" if has_video else f"{tipo} - {f.get('abr', '?')}kbps"
                formats.append({
                    "format_id": f["format_id"],
                    "label": label,
                    "filesize": f.get("filesize") or 0
                })

        # Remover duplicados pela label
        unique_formats = {f['label']: f for f in formats}
        formats = list(unique_formats.values())

        # Ordenar por qualidade
        import re
        def sort_key(f):
            label = f['label']
            base = 3 if "[Vídeo + Áudio]" in label else 2 if "[Vídeo]" in label else 1
            nums = re.findall(r'\d+', label)
            quality = int(nums[0]) if nums else 0
            return (base, quality)

        formats.sort(key=sort_key, reverse=True)

        return jsonify({"formats": formats})

    except yt_dlp.utils.ExtractorError as e:
        if "Sign in to confirm you’re not a bot" in str(e):
            return jsonify({"error": "Vídeo protegido: é necessário login no YouTube."}), 403
        else:
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url")
    format_id = request.form.get("format_id")

    if not url or not format_id:
        return jsonify({"error": "URL ou format_id em falta."}), 400

    video_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp4")

    ydl_opts = {
        "quiet": True,
        "format": format_id,
        "outtmpl": output_path,
        "cookiefile": COOKIES_FILE,
        "nocheckcertificate": True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        @after_this_request
        def remove_file(response):
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"Erro a apagar ficheiro: {e}")
            return response

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
