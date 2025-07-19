from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

COOKIES_FILE = "cookies.txt"  # O ficheiro de cookies exportado do browser

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.form["url"]
    
    print("Caminho do ficheiro cookies:", COOKIES_FILE)
    print("O ficheiro existe?", os.path.exists(COOKIES_FILE))

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

        # Remove duplicados pela label, mantendo o melhor formato (assumindo que o último é melhor)
        unique_formats = {}
        for f in formats:
            unique_formats[f['label']] = f
        formats = list(unique_formats.values())

        # Ordenar pela label (pode ajustar a lógica se quiseres)
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

