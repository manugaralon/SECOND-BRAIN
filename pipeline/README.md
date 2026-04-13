# Instagram → Obsidian Pipeline

Descarga audio de URLs de Instagram, transcribe con Groq Whisper, genera `.md` para Obsidian.

## Setup (una vez)

```bash
# 1. Instalar dependencias del sistema
sudo apt-get install -y ffmpeg

# 2. Instalar dependencias Python
pip3 install yt-dlp groq

# 3. Configurar API key de Groq (groq.com → free account → API Keys)
export GROQ_API_KEY='gsk_...'
# Para que persista, añádelo a ~/.bashrc:
echo "export GROQ_API_KEY='gsk_...'" >> ~/.bashrc
```

## Uso

```bash
cd /home/manuel/Desktop/PROJECTS/IMPENV/pipeline

# Procesar lista de URLs
python3 transcribe.py --urls urls.txt --output ./notes --topic "claude-env"

# URL única
python3 transcribe.py --url "https://www.instagram.com/reel/..." --topic "claude-env"

# Otros temas (cuando amplíes a más contenido)
python3 transcribe.py --urls urls_trading.txt --output ./notes --topic "trading"
python3 transcribe.py --urls urls_fisio.txt   --output ./notes --topic "fisioterapia"
```

## Añadir URLs

Edita `urls.txt` — una URL por línea. Las líneas con `#` se ignoran.

## Output

Cada vídeo genera un `.md` en `./notes/` con:
- Frontmatter YAML (título, URL, autor, duración, fecha, tags)
- Transcripción completa
- Descripción original
- Secciones para tus notas, ideas clave y referencias

Lleva estos `.md` a tu vault de Obsidian — o apunta `--output` directamente a la carpeta de tu vault.

## Idioma

Por defecto detecta español (`--language es`). Para autodetección: `--language auto`.
