"""
Fastest way to see real output: one direct call to DeepInfra, no DB, no
Redis, no FastAPI. Just the provider + prompt builder.

Usage:
    export DEEPINFRA_API_KEY=your-real-key
    python scripts/generate_one.py "Paneer Tikka" --stage draft
    python scripts/generate_one.py "Paneer Tikka" --stage final

Saves the result to ./output_<stage>.png and prints the cost.
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings  # noqa: E402
from app.inference.deepinfra import get_provider  # noqa: E402
from app.schemas import WizardAnswers  # noqa: E402
from app.services.prompt_builder import build_prompt  # noqa: E402


async def main(dish_name: str, stage: str):
    settings = get_settings()
    if not settings.DEEPINFRA_API_KEY or settings.DEEPINFRA_API_KEY == "test-key":
        print("ERROR: set a real DEEPINFRA_API_KEY env var first.")
        sys.exit(1)

    model = settings.DRAFT_MODEL if stage == "draft" else settings.FINAL_MODEL
    prompt = build_prompt(WizardAnswers(dish_name=dish_name))
    print(f"Model:  {model}")
    print(f"Prompt: {prompt}")

    provider = get_provider(settings)
    result = await provider.generate(prompt=prompt, model=model, size=settings.IMAGE_SIZE)

    out_path = f"output_{stage}.png"
    with open(out_path, "wb") as f:
        f.write(result.content)

    print(f"Saved: {out_path}")
    print(f"Cost:  ${result.cost_usd:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dish_name")
    parser.add_argument("--stage", choices=["draft", "final"], default="draft")
    args = parser.parse_args()
    asyncio.run(main(args.dish_name, args.stage))
