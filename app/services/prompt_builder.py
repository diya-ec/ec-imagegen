from app.schemas import WizardAnswers

_BASE = (
    "Professional food photography of {dish_name}, {cuisine_style}, "
    "served on {plating_style}, {background} background, {lighting}, "
    "{mood}, appetizing, high detail, shallow depth of field, no text, no watermark"
)

_DEFAULTS = {
    "cuisine_style": "classic presentation",
    "plating_style": "a clean plate",
    "background": "a neutral studio",
    "lighting": "soft natural lighting",
    "mood": "vibrant and appetizing",
}


_RESTYLE_BASE = (
    "Transform this into professional studio photography: soft directional "
    "lighting, shallow depth of field, clean styled background, high-end "
    "commercial photo quality, photorealistic, 4k. Keep the main subject "
    "unchanged - only improve lighting, background, and composition. "
    "Correct the camera framing to a proper professional product/food-photography "
    "shot: not an extreme close-up and not too far away - frame it the way a "
    "professional photographer would, with the subject filling a natural, "
    "well-composed portion of the frame at a flattering three-quarter or "
    "slightly elevated angle. Fix any awkward, too-close, too-far, or off-angle "
    "framing from the original photo while keeping the same dish, plate, and "
    "identity of the subject."
)

def build_prompt(answers: WizardAnswers) -> str:
    values = {"dish_name": answers.dish_name, **_DEFAULTS}
    for field, default in _DEFAULTS.items():
        provided = getattr(answers, field)
        if provided:
            values[field] = provided
    return _BASE.format(**values)

def build_restyle_prompt(extra_styling: str | None) -> str:
    if not extra_styling:
        return _RESTYLE_BASE
    return f"{_RESTYLE_BASE} Additional styling: {extra_styling}."