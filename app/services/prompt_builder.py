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

# _RESTYLE_BASE = (
#     "Transform this into professional studio photography: soft directional "
#     "lighting, shallow depth of field, clean styled background, high-end "
#     "commercial photo quality, photorealistic, 4k. Keep the main subject "
#     "unchanged - only improve lighting, background, and composition. "
#     "Correct the camera framing to a proper professional product/food-photography "
#     "shot: not an extreme close-up and not too far away - frame it the way a "
#     "professional photographer would, with the subject filling a natural, "
#     "well-composed portion of the frame at a flattering three-quarter or "
#     "slightly elevated angle. Fix any awkward, too-close, too-far, or off-angle "
#     "framing from the original photo while keeping the same dish, plate, and "
#     "identity of the subject."
# )

# # Rotated across a restyle batch (one per variation index, wrapping around if
# # MAX_RESTYLE_VARIATIONS ever exceeds len(this list)) so the N outputs are
# # deliberately distinct instead of relying on model randomness alone. Each
# # entry only nudges lighting/angle/mood — never subject, plate, or dish
# # identity, which the base prompt already locks down.
# RESTYLE_VARIATION_STYLES: list[str] = [
#     "Style: bright, airy natural daylight look, softly diffused, minimal "
#     "shadows, three-quarter angle.",
#     "Style: warm, moody restaurant lighting with gentle directional "
#     "shadows and a slightly elevated angle.",
#     "Style: crisp, high-contrast studio lighting on a clean, cool-toned "
#     "background, straight-on flattering angle.",
# ]

_RESTYLE_BASE = (
    "Turn this into a professional commercial food photograph. The dish "
    "itself must stay 100% identical - same food, same ingredients, same "
    "portion, same plate/bowl/container, same arrangement of items on it. "
    "Do not add, remove, rearrange, or restyle the food in any way. "
    "Everything else around the food should be rebuilt to professional "
    "studio quality: replace or clean up the background entirely with a "
    "clean, high-end commercial backdrop (neutral studio surface, softly "
    "blurred premium setting, or complementary color background), add "
    "realistic soft directional studio lighting with natural shadows and "
    "highlights on the food, add a shallow depth of field so the plate is "
    "sharp and the background gently falls out of focus, and remove any "
    "clutter, stains, distracting objects, cables, hands, or messy table "
    "surface from the original shot. "
    "This source photo may be a casual or low-quality phone photo - assume "
    "poor lighting, a messy or plain background, a slightly awkward angle, "
    "or an imperfect crop, and fully correct all of that. Reframe the shot "
    "to a proper professional product/food-photography composition: not an "
    "extreme close-up, not too far away, subject filling a natural, "
    "well-composed portion of the frame at a flattering three-quarter or "
    "slightly elevated angle, camera level and steady, no tilted horizon. "
    "Output should look like it was shot by a professional food "
    "photographer for a restaurant menu or ad - polished, appetizing, "
    "photorealistic, 4k, no text, no watermark, no logos."
)

# Rotated across a restyle batch (one per variation index, wrapping around if
# MAX_RESTYLE_VARIATIONS ever exceeds len(this list)) so the N outputs are
# deliberately distinct instead of relying on model randomness alone. Each
# entry only nudges lighting/angle/mood — never subject, plate, or dish
# identity, which the base prompt already locks down.
RESTYLE_VARIATION_STYLES: list[str] = [
    "Style: clean seamless white/light-grey studio backdrop, bright even "
    "natural daylight, minimal soft shadows, top-down or three-quarter angle.",
    "Style: natural textured surface background (wood, stone, or marble), "
    "warm ambient restaurant lighting with soft directional shadows, "
    "slightly elevated 45-degree angle.",
    "Style: dark, moody solid-color or gradient background, dramatic "
    "high-contrast studio lighting with defined highlights, straight-on "
    "eye-level angle.",
]


def build_prompt(answers: WizardAnswers) -> str:
    values = {"dish_name": answers.dish_name, **_DEFAULTS}
    for field, default in _DEFAULTS.items():
        provided = getattr(answers, field)
        if provided:
            values[field] = provided
    return _BASE.format(**values)


def build_restyle_prompt(extra_styling: str | None, variation_index: int = 0) -> str:
    """
    variation_index selects a rotating lighting/angle directive so a batch of
    restyle jobs produces visibly distinct results. Pass no index (or 0) to
    get the original single-variant behavior unchanged.
    """
    parts = [_RESTYLE_BASE]

    if RESTYLE_VARIATION_STYLES:
        style = RESTYLE_VARIATION_STYLES[variation_index % len(RESTYLE_VARIATION_STYLES)]
        parts.append(style)

    if extra_styling:
        parts.append(f"Additional styling: {extra_styling}.")

    return " ".join(parts)
