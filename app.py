from flask import Flask, render_template, request, send_file, jsonify
import yt_dlp
import os
import uuid

app = Flask(__name__)

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
    }

    try:
        formats = []
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            for f in info.get("formats", []):
                has_video = f.get("vcodec") != "none"
                has_audio = f.get("acodec") != "none"
                tipo = "[Vídeo + Áudio]" if has_video and has_audio else "[Vídeo]" if has_video else "[Áudio]"

                resolution = f.get("format_note") or f.get("height") or "?"
                if has_video:
                    label = f"{tipo} - {resolution}p"
                else:
                    label = f"{tipo} - {f.get('abr', '?')}kbps"

                formats.append({
                    "format_id": f["format_id"],
                    "label": label,
                    "filesize": f.get("filesize") or 0
                })

        formats = sorted({f['label']: f for f in formats}.values(), key=lambda x: x['label'], reverse=True)
        return jsonify({"formats": formats})
    except Exception as e:
        print("ERRO AO CARREGAR FORMATS:", e)
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
        "outtmpl": output_path
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return f"Erro: {e}", 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
