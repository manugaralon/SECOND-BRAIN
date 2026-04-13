#!/usr/bin/env python3
"""
Instagram → Obsidian Pipeline
Soporta vídeos, fotos y carruseles.

- Vídeo/Reel  → descarga audio → Groq Whisper (transcripción)
- Foto/Post   → descarga imagen(s) → Groq Vision (extracción de texto + descripción)
- Carrusel    → procesa cada imagen individualmente

Uso:
    python3 transcribe.py --urls urls.txt --output ./notes --topic "claude-env"
    python3 transcribe.py --url "https://www.instagram.com/p/..." --topic "trading"
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    print("ERROR: groq no instalado. Ejecuta: pip3 install groq")
    sys.exit(1)


GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".ogg"}

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
WHISPER_MODEL = "whisper-large-v3"


def check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ─── Metadatos ───────────────────────────────────────────────────────────────

COOKIES_FILE = str(Path(__file__).parent / "cookies.txt")


def _cookies_args() -> list[str]:
    if Path(COOKIES_FILE).exists():
        return ["--cookies", COOKIES_FILE]
    return []


def fetch_metadata(url: str) -> dict:
    """Obtiene metadatos de la URL sin descargar el contenido."""
    result = subprocess.run(
        ["yt-dlp", *_cookies_args(), "--dump-json", "--no-download", url],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            pass
    return {}


def detect_content_type(metadata: dict) -> str:
    """
    Detecta si el post es 'video', 'image' o 'carousel'.
    Devuelve 'video' por defecto si no hay información clara.
    """
    ext = metadata.get("ext", "")
    vcodec = metadata.get("vcodec", "")
    acodec = metadata.get("acodec", "")
    entries = metadata.get("entries")  # playlist/carrusel
    url_lower = metadata.get("webpage_url", "").lower()

    if entries:
        return "carousel"

    # Sin vídeo pero con imagen → es foto
    if vcodec in ("none", "") and ext in ("jpg", "jpeg", "png", "webp"):
        return "image"

    # Tiene stream de vídeo
    if vcodec and vcodec != "none":
        return "video"

    # Fallback por extensión
    if ext in ("jpg", "jpeg", "png", "webp"):
        return "image"

    return "video"


# ─── Descarga ────────────────────────────────────────────────────────────────

def _extract_shortcode(url: str) -> str | None:
    """Extrae el shortcode de una URL de Instagram."""
    import re
    m = re.search(r'/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)', url)
    return m.group(1) if m else None


def download_media(url: str, output_dir: str, as_audio_only: bool = False) -> list[str]:
    """
    Descarga el contenido de la URL en output_dir.
    Si as_audio_only=True, extrae solo el audio como mp3.
    Devuelve lista de rutas de archivos descargados.
    """
    output_template = os.path.join(output_dir, "%(autonumber)s_%(id)s.%(ext)s")

    if as_audio_only:
        cmd = [
            "yt-dlp",
            *_cookies_args(),
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "--output", output_template,
            "--no-playlist",
            url,
        ]
    else:
        cmd = [
            "yt-dlp",
            *_cookies_args(),
            "--output", output_template,
            "--no-playlist",
            url,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0:
        print(f"  [!] yt-dlp error: {result.stderr[-400:]}")
        return []

    return [str(p) for p in Path(output_dir).iterdir() if p.is_file()]


def download_images_instaloader(url: str, output_dir: str) -> list[str]:
    """
    Fallback para posts de solo imagen usando instaloader.
    Devuelve lista de rutas de imágenes descargadas.
    """
    shortcode = _extract_shortcode(url)
    if not shortcode:
        print("  [!] No se pudo extraer el shortcode de la URL")
        return []

    cmd = [
        "instaloader",
        "--no-videos",
        "--no-video-thumbnails",
        "--dirname-pattern", output_dir,
        "--filename-pattern", "{shortcode}_{typename}_{mediaid}",
        "--", f"-{shortcode}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    # instaloader puede devolver errores no fatales — revisar archivos descargados
    files = [str(p) for p in Path(output_dir).iterdir()
             if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    if not files:
        print(f"  [!] instaloader error: {result.stderr[-300:]}")
    return files


# ─── Procesado de contenido ──────────────────────────────────────────────────

def transcribe_audio(audio_path: str, client: Groq, language: str = "es") -> str:
    """Transcribe audio con Groq Whisper."""
    lang = None if language == "auto" else language
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), f),
            model=WHISPER_MODEL,
            language=lang,
            response_format="text",
        )
    return response


def extract_image_content(image_path: str, client: Groq) -> str:
    """
    Extrae texto e información de una imagen usando Groq Vision (Llama 4).
    Devuelve una descripción estructurada del contenido.
    """
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = Path(image_path).suffix.lower().lstrip(".")
    mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/jpeg")

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Analiza esta imagen de Instagram con detalle. "
                            "Haz lo siguiente:\n"
                            "1. TEXTO VISIBLE: Transcribe literalmente todo el texto que aparezca en la imagen "
                            "(incluyendo texto superpuesto, subtítulos, captions, títulos, listas, etc.).\n"
                            "2. CONTENIDO VISUAL: Describe brevemente lo que se ve (personas, gráficos, infografías, etc.).\n"
                            "3. MENSAJE PRINCIPAL: Resume en 1-2 frases la idea central que transmite.\n\n"
                            "Si no hay texto visible, concéntrate en describir el contenido visual con precisión."
                        ),
                    },
                ],
            }
        ],
        max_tokens=2000,
    )
    return response.choices[0].message.content


# ─── Generación de Markdown ──────────────────────────────────────────────────

def build_markdown(
    url: str,
    topic: str,
    content: str,
    metadata: dict,
    content_type: str,
    image_count: int = 1,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    raw_title = metadata.get("title") or metadata.get("description", "")
    title = (raw_title[:80].replace("\n", " ").strip()) if raw_title else f"Post {metadata.get('id', 'unknown')}"

    uploader = metadata.get("uploader") or metadata.get("channel", "desconocido")
    description = metadata.get("description", "")

    upload_date_raw = metadata.get("upload_date", "")
    upload_date = (
        f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:]}"
        if len(upload_date_raw) == 8 else upload_date_raw
    )

    # Metadatos específicos por tipo
    if content_type == "video":
        duration = metadata.get("duration", 0)
        duration = int(duration) if duration else 0
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "desconocida"
        type_meta = f"duration: {duration_str}"
        content_header = "## Transcripción"
        type_tag = "transcription"
    else:
        frames_str = f"{image_count} imagen{'es' if image_count > 1 else ''}"
        type_meta = f"images: {image_count}"
        content_header = f"## Contenido extraído ({frames_str})"
        type_tag = "vision"

    md = f"""---
title: "{title}"
url: "{url}"
topic: {topic}
type: {content_type}
author: {uploader}
{type_meta}
upload_date: {upload_date}
processed_date: {now}
tags:
  - {topic}
  - {type_tag}
---

# {title}

**Fuente:** [{uploader}]({url})
**Tipo:** {content_type} | **Subido:** {upload_date}

---

{content_header}

{content}

---

## Descripción original

{description[:500] if description else "_Sin descripción disponible_"}

---

## Notas personales

_[Espacio para tus notas]_

## Ideas clave

_[Las ideas más relevantes]_

## Referencias mencionadas

_[Links, nombres, conceptos del contenido]_
"""
    return md


# ─── Procesado por URL ───────────────────────────────────────────────────────

def process_url(url: str, topic: str, output_dir: Path, client: Groq, language: str = "es") -> bool:
    url = url.strip()
    if not url or url.startswith("#"):
        return True

    print(f"\n{'='*60}")
    print(f"URL: {url[:70]}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Metadatos
        print("  [1/4] Obteniendo metadatos...")
        metadata = fetch_metadata(url)
        content_type = detect_content_type(metadata)
        print(f"  [✓] Tipo detectado: {content_type}")

        # 2. Descarga
        print(f"  [2/4] Descargando {'audio' if content_type == 'video' else 'imagen(es)'}...")

        if content_type == "video":
            files = download_media(url, tmpdir, as_audio_only=True)
            audio_files = [f for f in files if Path(f).suffix.lower() in AUDIO_EXTENSIONS]
            if not audio_files:
                # Fallback: puede ser un post de imagen — usar instaloader
                print("  [!] Sin audio — reintentando con instaloader...")
                image_files = sorted(download_images_instaloader(url, tmpdir))
                if not image_files:
                    print("  [!] SKIP — ni audio ni imágenes encontrados")
                    return False
                content_type = "carousel" if len(image_files) > 1 else "image"
                print(f"  [✓] {len(image_files)} imagen(es) — procesando con Vision")
                print(f"  [3/4] Extrayendo contenido con Llama 4 Vision...")
                content_parts = []
                for i, img_path in enumerate(image_files, 1):
                    print(f"        Imagen {i}/{len(image_files)}...")
                    try:
                        img_content = extract_image_content(img_path, client)
                        content_parts.append(f"### Imagen {i}\n\n{img_content}" if len(image_files) > 1 else img_content)
                    except Exception as e:
                        print(f"  [!] Error en imagen {i}: {e}")
                        content_parts.append(f"### Imagen {i}\n\n_Error: {e}_")
                content = "\n\n---\n\n".join(content_parts)
                print(f"  [4/4] Generando .md...")
                md_content = build_markdown(url, topic, content, metadata, content_type, len(image_files))
                post_id = metadata.get("id") or datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in post_id)
                output_path = output_dir / f"{topic}_{safe_id}.md"
                output_path.write_text(md_content, encoding="utf-8")
                print(f"  [✓] Guardado: {output_path}")
                return True
            audio_path = audio_files[0]
            size_mb = os.path.getsize(audio_path) / 1024 / 1024
            print(f"  [✓] Audio: {Path(audio_path).name} ({size_mb:.1f} MB)")

            # 3. Transcribir
            print("  [3/4] Transcribiendo con Whisper...")
            try:
                content = transcribe_audio(audio_path, client, language)
                print(f"  [✓] {len(content)} caracteres transcritos")
            except Exception as e:
                print(f"  [!] Error transcribiendo: {e}")
                return False

        else:
            # Foto o carrusel
            files = download_media(url, tmpdir, as_audio_only=False)
            image_files = sorted(f for f in files if Path(f).suffix.lower() in IMAGE_EXTENSIONS)

            if not image_files:
                print("  [!] SKIP — no se encontraron imágenes")
                return False

            print(f"  [✓] {len(image_files)} imagen(es) descargada(s)")

            # 3. Extraer contenido de cada imagen
            print(f"  [3/4] Extrayendo contenido con Llama 4 Vision...")
            content_parts = []
            for i, img_path in enumerate(image_files, 1):
                print(f"        Imagen {i}/{len(image_files)}...")
                try:
                    img_content = extract_image_content(img_path, client)
                    if len(image_files) > 1:
                        content_parts.append(f"### Imagen {i}\n\n{img_content}")
                    else:
                        content_parts.append(img_content)
                except Exception as e:
                    print(f"  [!] Error en imagen {i}: {e}")
                    content_parts.append(f"### Imagen {i}\n\n_Error al procesar: {e}_")

            content = "\n\n---\n\n".join(content_parts)
            content_type = "carousel" if len(image_files) > 1 else "image"

        # 4. Generar .md
        print("  [4/4] Generando .md...")
        image_count = len(image_files) if content_type in ("image", "carousel") else 1
        md_content = build_markdown(url, topic, content, metadata, content_type, image_count)

        post_id = metadata.get("id") or datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in post_id)
        filename = f"{topic}_{safe_id}.md"

        output_path = output_dir / filename
        output_path.write_text(md_content, encoding="utf-8")
        print(f"  [✓] Guardado: {output_path}")

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pipeline Instagram → Obsidian .md (vídeos + fotos)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--urls", help="Archivo con URLs (una por línea)")
    group.add_argument("--url", help="URL única a procesar")
    parser.add_argument("--output", default="./notes", help="Carpeta de salida (default: ./notes)")
    parser.add_argument("--topic", default="general", help="Tema/tag para los archivos (default: general)")
    parser.add_argument("--language", default="es", help="Idioma audio: 'es', 'en', 'auto' (default: es)")
    args = parser.parse_args()

    if not GROQ_API_KEY:
        print("ERROR: Variable GROQ_API_KEY no configurada.")
        print("  export GROQ_API_KEY='gsk_...'")
        sys.exit(1)

    if not check_ffmpeg():
        print("ERROR: ffmpeg no instalado.")
        print("  sudo apt-get install -y ffmpeg")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = Groq(api_key=GROQ_API_KEY)

    if args.url:
        urls = [args.url]
    else:
        urls_file = Path(args.urls)
        if not urls_file.exists():
            print(f"ERROR: No existe {urls_file}")
            sys.exit(1)
        urls = [u.strip() for u in urls_file.read_text().splitlines() if u.strip() and not u.startswith("#")]

    print(f"Pipeline iniciado: {len(urls)} URL(s) → {output_dir} [tema: {args.topic}]")

    success, failed = 0, 0
    for url in urls:
        if process_url(url, args.topic, output_dir, client, args.language):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"Completado: {success} OK, {failed} fallidos")
    print(f"Archivos en: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
