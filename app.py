from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import base64
import tempfile

app = Flask(__name__)

# Base64 dos cookies.txt (mantém exatamente como tens, sem alterações)
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

# Decodifica e escreve os cookies para um ficheiro temporário (só uma vez no arranque)
cookies_bytes = base64.b64decode(COOKIES_BASE64.encode('utf-8'))
temp_cookies_file = tempfile.NamedTemporaryFile(delete=False, mode='wb', suffix='.txt')
temp_cookies_file.write(cookies_bytes)
temp_cookies_file.close()
COOKIES_FILE = temp_cookies_file.name  # Caminho temporário do ficheiro de cookies

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.form["url"]

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "cookiefile": COOKIES_FILE,
        "nocheckcertificate": True,  # Ajuda a evitar problemas SSL
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
                if has_video:
                    label = f"{tipo} - {resolution}"
                else:
                    label = f"{tipo} - {f.get('abr', '?')}kbps"

                formats.append({
                    "format_id": f["format_id"],
                    "label": label,
                    "filesize": f.get("filesize") or 0
                })

        # Remove duplicados pela label
        unique_formats = {}
        for f in formats:
            unique_formats[f['label']] = f
        formats = list(unique_formats.values())

        formats.sort(key=lambda x: x['label'], reverse=True)

        return jsonify({"formats": formats})

    except yt_dlp.utils.ExtractorError as e:
        if "Sign in to confirm you’re not a bot" in str(e):
            return jsonify({"error": "Vídeo protegido: é necessário login no YouTube para descarregar este vídeo."}), 403
        else:
            return jsonify({"error": str(e)}), 500

    except Exception as e:
        print("Erro geral:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/download", methods=["POST"])
def download():
    url = request.form["url"]
    format_id = request.form["format_id"]

    video_id = str(uuid.uuid4())
    output_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp4")

    ydl_opts = {
        "quiet": True,
        "format": format_id,
        "outtmpl": output_path,
        "cookiefile": COOKIES_FILE,
        "nocheckcertificate": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return f"Erro: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
