from pydantic import BaseModel


class CreateRestyleBatchRequest(BaseModel):
    """
    Not used directly by the router today (fields arrive as multipart Form
    fields alongside the photo UploadFile), kept as documentation of the
    logical request shape / for potential non-multipart callers.
    """
    restaurant_id: str | None = None
    menu_item_id: str | None = None
    extra_styling: str | None = None
    # the photo itself arrives as multipart UploadFile in the router, not here


class JobOut(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    id: int
    batch_id: str
    status: str
    model_used: str | None
    source_image_path: str | None
    is_selected: bool
    image_path: str | None
    cost_usd: float | None
    error_message: str | None


class RestyleBatchOut(BaseModel):
    batch_id: str
    jobs: list[JobOut]


class SelectRestyleRequest(BaseModel):
    job_id: int