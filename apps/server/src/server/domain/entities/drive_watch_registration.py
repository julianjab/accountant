from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DriveWatchRegistration:
    """The raw result of registering a push-notification channel with Drive.

    The use case attaches the remaining ``DriveWatchChannel`` fields
    (``id``, ``folder_id``, ``client_id``, ``page_token``) on top of this.
    """

    resource_id: str
    expires_at: datetime
