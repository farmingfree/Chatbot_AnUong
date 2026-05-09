"""Checkpoint system for resumable crawls"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class Checkpoint:
    """Save/load crawl state for resume capability"""

    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save(self, crawler_name: str, state: dict[str, Any]):
        """Save checkpoint state"""
        checkpoint_file = self.checkpoint_dir / f"{crawler_name}.json"

        state["_saved_at"] = datetime.utcnow().isoformat()

        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            logger.info(f"Checkpoint saved: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load(self, crawler_name: str) -> dict[str, Any] | None:
        """Load checkpoint state"""
        checkpoint_file = self.checkpoint_dir / f"{crawler_name}.json"

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            logger.info(f"Checkpoint loaded: {checkpoint_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def clear(self, crawler_name: str):
        """Clear checkpoint"""
        checkpoint_file = self.checkpoint_dir / f"{crawler_name}.json"

        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Checkpoint cleared: {checkpoint_file}")
