"""
Fastest way to see real restyle output: one direct call to Replicate, no DB,
no Redis, no FastAPI. Just the provider + prompt builder.

Usage:
    export REPLICATE_API_TOKEN=your-real-token
    python scripts/generate_one.py path/to/source_photo.jpg
    python scripts/generate_one.py path/to/source_photo.jpg --extra-styling "rustic wooden table"
    python scripts/generate_one.py path/to/source_photo.jpg --variation 1

Saves the result to ./output_restyle.jpg and prints the cost.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.inference.replicate_provider import get_restyle_provider  # noqa: E402
from app.services.prompt_builder import build_restyle_prompt  # noqa: E402


async def main(photo_path: str, extra_styling: str | None, variation: int):
    settings = get_settings()
    if not settings.REPLICATE_API_TOKEN:
        print("ERROR: set a real REPLICATE_API_TOKEN env var first.")
        sys.exit(1)

    with open(photo_path, "rb") as f:
        input_image = f.read()

    prompt = build_restyle_prompt(extra_styling, variation_index=variation)
    print(f"Model:  {settings.RESTYLE_MODEL}")
    print(f"Prompt: {prompt}")

    provider = get_restyle_provider(settings)
    result = await provider.generate(
        prompt=prompt,
        model=settings.RESTYLE_MODEL,
        size=settings.IMAGE_SIZE,
        input_image=input_image,
    )

    out_path = "output_restyle.jpg"
    with open(out_path, "wb") as f:
        f.write(result.content)

    print(f"Saved: {out_path}")
    print(f"Cost:  ${result.cost_usd:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("photo_path", help="Path to a source photo on disk")
    parser.add_argument("--extra-styling", default=None)
    parser.add_argument("--variation", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(main(args.photo_path, args.extra_styling, args.variation))