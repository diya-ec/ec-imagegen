from pydantic import BaseModel, Field


class WizardAnswers(BaseModel):
    """
    Guided-question answers from the merchant wizard — this is what gets
    turned into a prompt. No free-text prompting per product decision.
    """
    dish_name: str
    cuisine_style: str | None = None          # e.g. "North Indian", "Continental"
    plating_style: str | None = None          # e.g. "rustic wooden board", "minimal white plate"
    background: str | None = None             # e.g. "dark slate", "warm wooden table"
    lighting: str | None = None               # e.g. "natural daylight", "moody restaurant lighting"
    mood: str | None = None                   # e.g. "vibrant and appetizing", "elegant fine-dining"

class CreateRestyleJobRequest(BaseModel):
    restaurant_id: str
    menu_item_id: str
    extra_styling: str | None = None
    # the photo itself arrives as multipart UploadFile in the router, not here
class CreateDraftBatchRequest(BaseModel):
    restaurant_id: str
    menu_item_id: str
    wizard_answers: WizardAnswers


class JobOut(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}

    id: int
    batch_id: str
    stage: str
    status: str
    model_used: str | None
    regen_count: int
    source_image_path: str | None
    is_selected: bool
    image_path: str | None
    cost_usd: float | None
    error_message: str | None


class DraftBatchOut(BaseModel):
    batch_id: str
    jobs: list[JobOut]


class RestyleBatchOut(BaseModel):
    batch_id: str
    jobs: list[JobOut]


class SelectDraftRequest(BaseModel):
    draft_job_id: int


class SelectRestyleRequest(BaseModel):
    job_id: int


class RegenerateFinalRequest(BaseModel):
    batch_id: str
