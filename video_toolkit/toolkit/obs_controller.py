"""
OBS WebSocket 5.x Controller
=============================
Controls OBS Studio via obsws-python for recording, scene switching,
source visibility, and screenshot capture.

Usage:
    with OBSController(config) as obs:
        obs.switch_scene("App Fullscreen")
        obs.start_recording()
        # ... automation happens ...
        obs.stop_recording()
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class OBSController:
    """
    Controls OBS Studio via the WebSocket 5.x API (obsws-python).

    Parameters
    ----------
    config : dict
        The 'obs' section from config.yaml.
    """

    def __init__(self, config: dict) -> None:
        self.host: str = config.get("host", "localhost")
        self.port: int = config.get("port", 4455)
        self.password: str = config.get("password", "")
        self.scenes: dict = config.get("scenes", {})
        self._client: Any = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "OBSController":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, retries: int = 3, delay: float = 2.0) -> None:
        """Connect to OBS WebSocket server with retries."""
        try:
            import obsws_python as obs  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "obsws-python is not installed. Run: pip install obsws-python"
            ) from exc

        for attempt in range(1, retries + 1):
            try:
                logger.info(
                    "Connecting to OBS WebSocket %s:%s (attempt %d/%d)...",
                    self.host, self.port, attempt, retries,
                )
                self._client = obs.ReqClient(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    timeout=10,
                )
                version_info = self._client.get_version()
                logger.info(
                    "Connected to OBS %s (WebSocket %s)",
                    version_info.obs_version,
                    version_info.obs_web_socket_version,
                )
                # Log available scenes for diagnostic purposes
                try:
                    resp = self._client.get_scene_list()
                    scene_names = [s["sceneName"] for s in resp.scenes]
                    logger.info("Available OBS scenes: %s", scene_names)
                except Exception:  # noqa: BLE001
                    pass
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Connection attempt %d failed: %s", attempt, exc)
                if attempt < retries:
                    time.sleep(delay)
        raise ConnectionError(
            f"Could not connect to OBS at {self.host}:{self.port} after {retries} attempts. "
            "Ensure OBS is running and WebSocket Server is enabled."
        )

    def disconnect(self) -> None:
        """Disconnect from OBS WebSocket server."""
        if self._client is not None:
            try:
                self._client.disconnect()
                logger.info("Disconnected from OBS.")
            except Exception as exc:  # noqa: BLE001
                logger.debug("Error during disconnect: %s", exc)
            finally:
                self._client = None

    def _require_client(self) -> Any:
        if self._client is None:
            raise RuntimeError("Not connected to OBS. Call connect() first.")
        return self._client

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------

    def switch_scene(self, scene_name: str) -> None:
        """Switch to a named OBS scene."""
        client = self._require_client()
        try:
            client.set_current_program_scene(scene_name)
            logger.info("Switched to scene: %s", scene_name)
        except Exception as exc:
            logger.error("Failed to switch to scene '%s': %s", scene_name, exc)
            raise

    def get_current_scene(self) -> str:
        """Return the name of the currently active scene."""
        client = self._require_client()
        resp = client.get_current_program_scene()
        return resp.scene_name

    def list_scenes(self) -> list[str]:
        """Return a list of all scene names."""
        client = self._require_client()
        resp = client.get_scene_list()
        return [s["sceneName"] for s in resp.scenes]

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        """Start OBS recording."""
        client = self._require_client()
        try:
            client.start_record()
            logger.info("Recording started.")
        except Exception as exc:
            logger.error("Failed to start recording: %s", exc)
            raise

    def stop_recording(self) -> Optional[str]:
        """
        Stop OBS recording.

        Returns
        -------
        str or None
            Path to the recorded file if available.
        """
        client = self._require_client()
        try:
            resp = client.stop_record()
            output_path: str = getattr(resp, "output_path", "")
            logger.info("Recording stopped. Output: %s", output_path or "(unknown)")
            return output_path or None
        except Exception as exc:
            logger.error("Failed to stop recording: %s", exc)
            raise

    def pause_recording(self) -> None:
        """Pause an active OBS recording."""
        client = self._require_client()
        client.pause_record()
        logger.info("Recording paused.")

    def resume_recording(self) -> None:
        """Resume a paused OBS recording."""
        client = self._require_client()
        client.resume_record()
        logger.info("Recording resumed.")

    def get_recording_status(self) -> dict:
        """
        Return current recording status.

        Returns
        -------
        dict with keys: active (bool), paused (bool), timecode (str), bytes (int)
        """
        client = self._require_client()
        resp = client.get_record_status()
        return {
            "active": resp.output_active,
            "paused": resp.output_paused,
            "timecode": getattr(resp, "output_timecode", ""),
            "bytes": getattr(resp, "output_bytes", 0),
        }

    def wait_for_recording_start(self, timeout: float = 10.0, poll: float = 0.5) -> None:
        """Block until OBS reports recording as active (or timeout)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get_recording_status()
            if status["active"]:
                logger.info("Recording confirmed active.")
                return
            time.sleep(poll)
        raise TimeoutError(f"Recording did not start within {timeout}s.")

    # ------------------------------------------------------------------
    # Source visibility
    # ------------------------------------------------------------------

    def set_source_visibility(
        self, scene_name: str, source_name: str, visible: bool
    ) -> None:
        """Show or hide a source within a scene."""
        client = self._require_client()
        try:
            resp = client.get_scene_item_id(scene_name, source_name)
            item_id = resp.scene_item_id
            client.set_scene_item_enabled(scene_name, item_id, visible)
            logger.info(
                "Source '%s' in scene '%s' set to visible=%s",
                source_name, scene_name, visible,
            )
        except Exception as exc:
            logger.error(
                "Failed to set visibility for source '%s': %s", source_name, exc
            )
            raise

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def take_screenshot(
        self,
        source_name: Optional[str] = None,
        file_path: Optional[str] = None,
        width: int = 1920,
        height: int = 1080,
        quality: int = -1,
    ) -> str:
        """
        Capture a screenshot from OBS.

        Parameters
        ----------
        source_name : str, optional
            If provided, capture the named source; otherwise capture the current scene.
        file_path : str, optional
            Where to save the PNG. Auto-generated if not provided.
        width, height : int
            Output resolution.
        quality : int
            JPEG quality (-1 = default).

        Returns
        -------
        str
            Path to the saved screenshot file.
        """
        client = self._require_client()
        if file_path is None:
            ts = int(time.time())
            file_path = str(Path.cwd() / f"screenshot_{ts}.png")

        if source_name:
            resp = client.get_source_screenshot(source_name, "png", width, height, quality)
        else:
            current_scene = self.get_current_scene()
            resp = client.get_source_screenshot(current_scene, "png", width, height, quality)

        import base64
        img_data = resp.image_data  # "data:image/png;base64,..."
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]
        Path(file_path).write_bytes(base64.b64decode(img_data))
        logger.info("Screenshot saved: %s", file_path)
        return file_path

    # ------------------------------------------------------------------
    # Convenience scene helpers
    # ------------------------------------------------------------------

    def show_diagram_overlay(self, visible: bool = True) -> None:
        """Toggle the Diagram Overlay scene (Browser Source with HTML diagram)."""
        if visible:
            self.switch_scene(self.scenes.get("diagram_overlay", "Diagram Overlay"))
        else:
            self.switch_scene(self.scenes.get("app_scene", "App Fullscreen"))

    def transition_to_app(self) -> None:
        """Switch to the main app scene."""
        self.switch_scene(self.scenes.get("app_scene", "App Fullscreen"))

    def transition_to_intro(self) -> None:
        """Switch to the intro scene."""
        self.switch_scene(self.scenes.get("intro_scene", "Intro"))

    def transition_to_outro(self) -> None:
        """Switch to the outro scene."""
        self.switch_scene(self.scenes.get("outro_scene", "Outro"))
