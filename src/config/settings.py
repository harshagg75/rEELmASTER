import os

from dotenv import load_dotenv

load_dotenv()

# ── Model names ───────────────────────────────────────────────────────────────
MODEL_ORCHESTRATOR: str = "claude-opus-4-6"
MODEL_AGENT: str = "claude-sonnet-4-6"

# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY: str = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", os.environ["SUPABASE_ANON_KEY"])
SUPABASE_DB_URL: str = os.environ["SUPABASE_DB_URL"]

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]

# ── Account context ───────────────────────────────────────────────────────────
IG_HANDLE: str = os.getenv("IG_HANDLE", "ekfollowekchara")
IG_NICHE: str = os.getenv("IG_NICHE", "motivational,lifestyle,cultural")
IG_TIMEZONE: str = os.getenv("IG_TIMEZONE", "Asia/Kolkata")
TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "Hindi-English")

# ── Local paths ───────────────────────────────────────────────────────────────
CLIPS_DIR: str = os.getenv("CLIPS_DIR", "./clips")
OUTPUTS_DIR: str = os.getenv("OUTPUTS_DIR", "./outputs")
AUDIO_DIR: str = os.getenv("AUDIO_DIR", "./audio")

# ── Embeddings ────────────────────────────────────────────────────────────────
# paraphrase-multilingual-MiniLM-L12-v2 supports Hindi+English, 384 dims
EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSION: int = 384

# ── Pipeline ──────────────────────────────────────────────────────────────────
QA_MAX_REVISIONS: int = 3
MAX_CLIPS_PER_REEL: int = 8
MIN_CLIP_DURATION_SEC: float = 3.0
MAX_CLIP_DURATION_SEC: float = 15.0
TARGET_REEL_MIN_SEC: int = 15
TARGET_REEL_MAX_SEC: int = 60
