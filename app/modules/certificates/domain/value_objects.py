"""
Certificate Value Objects
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CertificateNumber:
    """Certificate unique identifier"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Certificate number cannot be empty")

    @classmethod
    def generate(cls, registration_id: int, event_id: int) -> 'CertificateNumber':
        """Generate certificate number from registration and event"""
        year = datetime.utcnow().year
        return cls(f"GLCG-{year}-{event_id:04d}-{registration_id:05d}")


@dataclass(frozen=True)
class CertificateUrl:
    """Certificate file URL"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Certificate URL cannot be empty")
        if not self.value.startswith(('http://', 'https://')):
            raise ValueError("Certificate URL must be HTTP(S)")


@dataclass(frozen=True)
class DownloadCount:
    """Number of times certificate downloaded"""
    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Download count cannot be negative")

    def increment(self) -> 'DownloadCount':
        """Increment download count"""
        return DownloadCount(self.value + 1)

    @classmethod
    def zero(cls) -> 'DownloadCount':
        return cls(0)
