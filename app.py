from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid
import base64
import tempfile

app = Flask(__name__)

# Base64 dos cookies.txt (codificado manualmente)
COOKIES_BASE64 = """
IyBOZXRzY2FwZSBIVFRQIENvb2tpZSBGaWxlDQojIFRoaXMgZmlsZSBpcyBnZW5l
cmF0ZWQgYnkgeXQtZGxwLiAgRG8gbm90IGVkaXQuDQoNCi55b3V0dWJlLmNvbQlU
UlVFCS8JRkFMU0UJMAlQUkVGCWhsPWVuJnR6PVVUQw0KLnlvdXR1YmUuY29tCVRS
VUUJLwlUUlVFCTAJU09DUwlDQUkNCi55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkw
CVlTQwkycFRud2NRd2l3NA0KLnlvdXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3Njg0
NDA3MDgJX19TZWN1cmUtUk9MTE9VVF9UT0tFTglDUDdTcXZiRzY1LXAxd0VRdDd5
a3B1UEhqZ01ZN3B2Q3B1UEhqZ00lM0QNCi55b3V0dWJlLmNvbQlUUlVFCS8JVFJV
RQkxNzY4NDQ1NDIxCVZJU0lUT1JfSU5GTzFfTElWRQljUFF3OWNsdnowYw0KLnlv
dXR1YmUuY29tCVRSVUUJLwlUUlVFCTE3Njg0NDU0MjEJVklTSVRPUl9QUklWQUNZ
X01FVEFEQVRBCUNnSlFWQkloRWgwU0d3c01EZzhRRVJJVEZCVVdGeGdaR2hzY0hS
NGZJQ0VpSXlRbEppQWYNCi55b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxODE1OTY1
NDIxCV9fU2VjdXJlLVlUX1RWRkFTCXQ9NDg2OTEzJnM9Mg0KLnlvdXR1YmUuY29t
CVRSVUUJLwlUUlVFCTE3Njg0NDU0MjEJREVWSUNFX0lORk8JQ2h4T2VsVjVUMFJW
TlU5VVdUTk9SR013VG1wck5VNUVTVEpPUVQwOUVPMlA3TU1HR0lUcjY4TUcNCi55
b3V0dWJlLmNvbQlUUlVFCS8JVFJVRQkxNzUyODk0NzM1CUdQUwkxDQoueW91dHVi
ZS5jb20JVFJVRQkvdHYJVFJVRQkxNzg1NzI1NDIxCV9fU2VjdXJlLVlUX0RFUlAJ
Q0tDeDVKVS0NCg==
"""

# Decodifica e escreve os cookies para um ficheiro temporário
cookies_bytes = base64.b64decode(COOKIES_BASE64)
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
        "cookiefile": COOKIES_FILE
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
        "cookiefile": COOKIES_FILE
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return f"Erro: {e}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
