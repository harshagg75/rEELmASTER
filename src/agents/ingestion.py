import json

from loguru import logger

from src.config import prompts as P
from src.config import settings as S
from src.memory.schema import ClipMetadata
from src.tools.claude_client import call_claude, parse_json_response
from src.tools.vector_db import VectorDB


class ClipIngestionAgent:
    """
    Agent 01 — Clip Ingestion.
    Calls Claude Sonnet to analyse a clip, then optionally embeds and stores to Supabase.
    Pass dry_run=True to skip all DB operations (useful for testing and --dry-run CLI).
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        if not dry_run:
            self.db = VectorDB()

    def run(
        self,
        clip_path: str,
        ffprobe_data: dict,
        transcript: str,
    ) -> ClipMetadata:
        logger.info(f"[IngestionAgent] Analysing {clip_path}")

        user_msg = self._build_prompt(clip_path, ffprobe_data, transcript)

        try:
            raw = call_claude(P.INGESTION_PROMPT, user_msg, model=S.MODEL_AGENT)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[IngestionAgent] Claude call failed for {clip_path}: {e}")
            raise

        # Python-computed segments are authoritative — override Claude's derivation
        if "usable_segments" in ffprobe_data and ffprobe_data["usable_segments"]:
            data["usable_segments"] = ffprobe_data["usable_segments"]

        try:
            metadata = ClipMetadata(**data)
        except Exception as e:
            logger.error(f"[IngestionAgent] Schema validation failed: {e}\nData: {data}")
            raise

        if not self.dry_run:
            embedding_text = self._build_embedding_text(metadata)
            metadata.embedding = self.db.embed(embedding_text)
            self.db.upsert_clip(metadata)
            logger.success(
                f"[IngestionAgent] Stored {metadata.clip_id} | "
                f"score={metadata.quality_score:.1f} | mood={metadata.mood}"
            )
        else:
            logger.info(
                f"[IngestionAgent] [DRY RUN] {metadata.clip_id} | "
                f"score={metadata.quality_score:.1f} | mood={metadata.mood}"
            )

        return metadata

    # ── Private helpers ────────────────────────────────────────────────────────

    def _build_prompt(self, clip_path: str, ffprobe_data: dict, transcript: str) -> str:
        return (
            f"clip_path: {clip_path}\n\n"
            f"ffprobe_data:\n{json.dumps(ffprobe_data, indent=2)}\n\n"
            f"transcript:\n{transcript if transcript else '(no speech detected)'}\n\n"
            "Analyse this clip for @ekfollowekchara and return the JSON metadata."
        )

    def _build_embedding_text(self, m: ClipMetadata) -> str:
        """
        Build a rich text description of the clip for semantic embedding.
        Uses content properties, NOT the filename — so search finds by meaning.
        """
        parts = [
            f"shot type: {m.shot_type}",
            f"mood: {m.mood}",
            f"color palette: {m.color_palette}",
            f"scene: {', '.join(m.scene_tags)}",
            f"emotions: {', '.join(m.emotion_tags)}",
            f"transcript: {m.transcript_summary}",
            f"movement energy: {m.movement_energy}",
            f"face present: {'yes' if m.face_present else 'no'}",
        ]
        return ". ".join(parts)
