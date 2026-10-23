"""Typed errors for the YouCam client, with user-facing hints."""
from __future__ import annotations

# Engine error codes from the docs mapped to advice a shopper can act on.
ENGINE_HINTS = {
    "error_no_face": "We couldn't find a face. Face the camera in good light.",
    "error_src_face_too_small": "Move closer: your face should fill most of the oval.",
    "error_src_face_out_of_bound": "Keep your whole face inside the frame.",
    "error_lighting_dark": "The photo is too dark. Face a window or a bright light.",
    "error_below_min_image_size": "This photo is too small. Use a sharper photo.",
    "error_exceed_max_image_size": "This photo is too large for the AI. Try again.",
    "error_face_angle_invalid": "Look straight at the camera (head within 10 degrees).",
    "error_face_position_too_small": "Move closer to the camera.",
    "error_face_position_out_of_boundary": "Your face is cut off. Step back a little.",
    "error_face_pose": "Turn your face towards the camera.",
    "error_large_face_angle": "Turn your face towards the camera.",
    "error_multiple_people": "Only one person should be in the photo.",
    "error_nsfw_content_detected": "This photo can't be processed.",
    "PHOTO_DETECTION_FAIL": "We couldn't find your ear or neck. Use a head-and-shoulders photo.",
    "PHOTO_CHECK_INVALID": "Face the camera with your neck and ears visible.",
    "OBJECT_DETECTION_FAIL": "That jewellery image couldn't be read.",
}


class YouCamError(Exception):
    """HTTP-level failure (4xx/5xx) from the YouCam API."""

    def __init__(self, status: int, code: str | None, message: str | None = None):
        self.status = status
        self.code = code or "unknown"
        self.message = message or ""
        super().__init__(f"YouCam {status} {self.code}: {self.message}")

    @property
    def hint(self) -> str:
        if self.code == "CreditInsufficiency":
            return "The demo has used its YouCam units for now. Sample results still work."
        if self.status == 401:
            return "The YouCam API key is missing or invalid."
        if self.status == 429:
            return "Too many requests right now. Please retry in a minute."
        return "The YouCam API rejected this request."


class YouCamEngineError(Exception):
    """The task ran but the AI engine returned task_status=error (no units are charged)."""

    def __init__(self, code: str | None, message: str | None = None, task_id: str | None = None):
        self.code = code or "unknown_internal_error"
        self.message = message or ""
        self.task_id = task_id
        super().__init__(f"YouCam engine error {self.code}: {self.message}")

    @property
    def hint(self) -> str:
        return ENGINE_HINTS.get(self.code, "The AI couldn't process this photo. Try another one.")


class YouCamTimeout(Exception):
    pass


class BudgetExceeded(Exception):
    """Our own guard: refuse live calls that would break the unit budget."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)
