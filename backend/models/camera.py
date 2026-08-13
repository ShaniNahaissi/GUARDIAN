from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from dal.database import Base


class Camera(Base):
    """Mirrors schemas.camera.CameraInfo field-for-field -- no camelCase/snake_case
    translation needed at the API boundary."""
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    location: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="normal")
    statusText: Mapped[str] = mapped_column(String(32), nullable=False, default="NORMAL")
    imageUrl: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    time: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    primaryPhone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    additionalPhone: Mapped[str] = mapped_column(String(256), nullable=False, default="")
