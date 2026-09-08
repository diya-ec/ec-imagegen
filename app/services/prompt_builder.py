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


def build_prompt(answers: WizardAnswers) -> str:
    values = {"dish_name": answers.dish_name, **_DEFAULTS}
    for field, default in _DEFAULTS.items():
        provided = getattr(answers, field)
        if provided:
            values[field] = provided
    return _BASE.format(**values)
