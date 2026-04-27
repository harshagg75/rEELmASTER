from __future__ import annotations

from loguru import logger

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("[VectorDB] sentence-transformers not installed. Embeddings unavailable.")

try:
    from supabase import create_client, Client
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False
    logger.warning("[VectorDB] supabase-py not installed. Database operations unavailable.")

from src.config import settings
from src.memory.schema import ClipMetadata

_embedding_model: "SentenceTransformer | None" = None
_supabase: "Client | None" = None


def _get_embedding_model() -> "SentenceTransformer":
    global _embedding_model
    if not _ST_AVAILABLE:
        raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    if _embedding_model is None:
        logger.info(f"[VectorDB] Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.success(f"[VectorDB] Embedding model loaded ({settings.EMBEDDING_DIMENSION} dims).")
    return _embedding_model


def _get_client() -> "Client":
    global _supabase
    if not _SUPABASE_AVAILABLE:
        raise ImportError("supabase-py not installed. Run: pip install supabase")
    if _supabase is None:
        _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase


class VectorDB:
    """Supabase + pgvector client. All methods are lazy — no connection at init."""

    def embed(self, text: str) -> list[float]:
        """Generate a normalised embedding vector from text."""
        model = _get_embedding_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def upsert_clip(self, metadata: ClipMetadata) -> None:
        """Insert or update a clip record in the clips table."""
        client = _get_client()
        row: dict = {
            "clip_id": metadata.clip_id,
            "file_path": metadata.file_path,
            "quality_score": metadata.quality_score,
            "quality_flag": metadata.quality_flag,
            "shot_type": metadata.shot_type,
            "movement_energy": metadata.movement_energy,
            "scene_tags": metadata.scene_tags,
            "emotion_tags": metadata.emotion_tags,
            "face_present": metadata.face_present,
            "transcript_summary": metadata.transcript_summary,
            "mood": metadata.mood,
            "color_palette": metadata.color_palette,
            "usable_segments": [s.model_dump() for s in metadata.usable_segments],
            "embedding": metadata.embedding,
            "usage_count": metadata.usage_count,
            "performance_score": metadata.performance_score,
            "performance_tier": metadata.performance_tier,
        }
        client.table("clips").upsert(row, on_conflict="clip_id").execute()
        logger.debug(f"[VectorDB] Upserted clip: {metadata.clip_id}")

    def clip_exists(self, clip_id: str) -> bool:
        """Return True if clip_id is already indexed."""
        client = _get_client()
        result = (
            client.table("clips")
            .select("clip_id")
            .eq("clip_id", clip_id)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    def get_all_clip_ids(self) -> set[str]:
        """Return all indexed clip_ids (for --resume mode)."""
        client = _get_client()
        all_ids: set[str] = set()
        offset = 0
        limit = 1000
        while True:
            result = (
                client.table("clips")
                .select("clip_id")
                .range(offset, offset + limit - 1)
                .execute()
            )
            if not result.data:
                break
            for row in result.data:
                all_ids.add(row["clip_id"])
            if len(result.data) < limit:
                break
            offset += limit
        return all_ids

    def similarity_search(
        self,
        query_text: str,
        limit: int = 20,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        Vector similarity search against clips table.
        filters: optional SQL-compatible equality filters e.g. {"quality_flag": "usable"}
        """
        client = _get_client()
        query_vec = self.embed(query_text)

        query = (
            client.table("clips")
            .select("*")
            .order("embedding", desc=False)  # placeholder — real cosine search via RPC
        )
        # Apply column filters
        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)

        # Use Supabase RPC for proper cosine similarity when available
        try:
            result = client.rpc(
                "search_clips",
                {"query_embedding": query_vec, "match_count": limit},
            ).execute()
            return result.data or []
        except Exception:
            # Fallback: basic select without vector ordering (used in dev without RPC)
            logger.warning("[VectorDB] search_clips RPC not available — returning unranked results.")
            result = client.table("clips").select("*").limit(limit).execute()
            return result.data or []
