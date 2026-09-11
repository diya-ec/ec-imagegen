"""
Builds the prompt sent to the restyle (image-to-image) provider. This
service no longer does text-to-image generation, so there is no wizard-based
prompt builder — only the restyle prompt.
"""

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

# Rotated across a restyle batch (one per variation index, wrapping around if
# MAX_RESTYLE_VARIATIONS ever exceeds len(this list)) so the N outputs are
# deliberately distinct instead of relying on model randomness alone. Each
# entry only nudges lighting/angle/mood — never subject, plate, or dish
# identity, which the base prompt already locks down.
RESTYLE_VARIATION_STYLES: list[str] = [
    "Style: bright, airy natural daylight look, softly diffused, minimal "
    "shadows, three-quarter angle.",
    "Style: warm, moody restaurant lighting with gentle directional "
    "shadows and a slightly elevated angle.",
    "Style: crisp, high-contrast studio lighting on a clean, cool-toned "
    "background, straight-on flattering angle.",
]


def build_restyle_prompt(extra_styling: str | None, variation_index: int = 0) -> str:
    """
    variation_index selects a rotating lighting/angle directive so a batch of
    restyle jobs produces visibly distinct results.
    """
    parts = [_RESTYLE_BASE]

    if RESTYLE_VARIATION_STYLES:
        style = RESTYLE_VARIATION_STYLES[variation_index % len(RESTYLE_VARIATION_STYLES)]
        parts.append(style)

    if extra_styling:
        parts.append(f"Additional styling: {extra_styling}.")

    return " ".join(parts)