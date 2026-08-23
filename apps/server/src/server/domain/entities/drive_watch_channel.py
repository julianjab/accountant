from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DriveWatchChannel:
    """A Google Drive push-notification subscription for a folder.

    ``page_token`` is the Changes-API cursor this channel has processed up to;
    it advances every time a notification is handled. ``token`` is this
    channel's own shared secret, echoed back by Drive on every notification and
    never returned to API callers.
    """

    id: str
    resource_id: str
    folder_id: str
    client_id: str
    token: str
    page_token: str
    expires_at: datetime
