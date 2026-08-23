from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DriveWatchChannel:
    """A Google Drive push-notification subscription for a folder."""

    id: str
    resource_id: str
    folder_id: str
    expires_at: datetime
