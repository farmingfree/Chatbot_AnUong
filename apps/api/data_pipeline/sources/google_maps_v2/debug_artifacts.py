"""
Debug artifacts manager for saving crawl evidence.
"""
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime
from playwright.async_api import Page


class DebugArtifacts:
    """
    Saves debug artifacts for every crawled place.

    Artifacts:
    - raw HTML snapshot
    - extracted JSON data
    - screenshot
    - extraction metadata
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_place_dir(self, place_id: str) -> Path:
        """Get directory for a specific place's artifacts."""
        place_dir = self.base_dir / place_id
        place_dir.mkdir(parents=True, exist_ok=True)
        return place_dir

    async def save_all(
        self,
        page: Page,
        place_id: str,
        extracted_data: Dict[str, Any],
        validation_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Save all debug artifacts for a place.

        Returns dict of saved file paths.
        """
        place_dir = self.get_place_dir(place_id)
        saved_files = {}

        # 1. Save screenshot
        screenshot_path = place_dir / "screenshot.png"
        try:
            await page.screenshot(path=str(screenshot_path), full_page=False)
            saved_files['screenshot'] = str(screenshot_path)
        except Exception as e:
            saved_files['screenshot_error'] = str(e)

        # 2. Save raw HTML
        html_path = place_dir / "raw.html"
        try:
            html_content = await page.content()
            html_path.write_text(html_content, encoding='utf-8')
            saved_files['html'] = str(html_path)
        except Exception as e:
            saved_files['html_error'] = str(e)

        # 3. Save extracted JSON
        json_path = place_dir / "extracted.json"
        try:
            json_path.write_text(
                json.dumps(extracted_data, ensure_ascii=False, indent=2, default=str),
                encoding='utf-8'
            )
            saved_files['json'] = str(json_path)
        except Exception as e:
            saved_files['json_error'] = str(e)

        # 4. Save validation results
        if validation_results:
            validation_path = place_dir / "validation.json"
            try:
                validation_path.write_text(
                    json.dumps(validation_results, ensure_ascii=False, indent=2, default=str),
                    encoding='utf-8'
                )
                saved_files['validation'] = str(validation_path)
            except Exception as e:
                saved_files['validation_error'] = str(e)

        # 5. Save metadata
        metadata_path = place_dir / "metadata.json"
        try:
            metadata = {
                'place_id': place_id,
                'timestamp': datetime.utcnow().isoformat(),
                'url': page.url,
                'saved_files': saved_files
            }
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
            saved_files['metadata'] = str(metadata_path)
        except Exception as e:
            saved_files['metadata_error'] = str(e)

        return saved_files

    def load_extracted_data(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Load previously extracted data for a place."""
        place_dir = self.get_place_dir(place_id)
        json_path = place_dir / "extracted.json"

        if not json_path.exists():
            return None

        try:
            return json.loads(json_path.read_text(encoding='utf-8'))
        except:
            return None

    def list_places(self) -> list[str]:
        """List all place IDs with saved artifacts."""
        return [d.name for d in self.base_dir.iterdir() if d.is_dir()]
