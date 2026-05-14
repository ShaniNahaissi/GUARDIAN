from pydantic import BaseModel, ConfigDict, Field


class CameraInfo(BaseModel):
    id: str
    name: str
    location: str
    status: str = Field(default="normal")
    statusText: str = Field(default="NORMAL")
    imageUrl: str = Field(default="")
    time: str = Field(default="")


class CameraCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    location: str = ""
    imageUrl: str | None = None
    stream_uuid: str | None = Field(default=None, alias="streamUuid")


class CameraUpdateRequest(BaseModel):
    name: str | None = None
    location: str | None = None
    imageUrl: str | None = None


class SystemStats(BaseModel):
    activeCameras: int
    activeOnline: int
    warningAlerts: int
    majorAlerts: int
    criticalAlerts: int
