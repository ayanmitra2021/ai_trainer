"""Diagnostic script — verify NVIDIA NIM connectivity and find available models.

Run from the backend directory:
    py tools/check_nvidia.py

What it checks:
  1. Prints which API key and model are loaded from config (key is redacted).
  2. Validates the key format (must start with "nvapi-").
  3. Lists every model available on your account via the /models endpoint.
  4. Probes a curated set of Nemotron / NVIDIA candidate models and shows which ones work.
  5. Makes a full structured-output round-trip with the configured model.
"""

import asyncio
import json
import sys
from pathlib import Path

# ── Make the app importable from tools/ ──────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import openai
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()

# ── Candidate models to probe (best→smallest / most→least capable) ───────────
# Add any model IDs you want to test here.
CANDIDATE_MODELS = [
    "nvidia/llama-3.1-nemotron-ultra-253b-v1",
    "nvidia/llama-3.3-nemotron-super-49b-v1",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "nvidia/nemotron-4-340b-instruct",
    "nvidia/nemotron-mini-4b-instruct",
    "nvidia/llama-3.1-nemotron-nano-8b-v1",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
]


class _Ping(BaseModel):
    ok: bool


async def main() -> None:
    api_key = settings.nvidia_api_key
    base_url = settings.nvidia_base_url.rstrip("/")
    model_id = settings.nvidia_model_id
    provider = settings.app_brain_model

    print(f"\n{'='*60}")
    print("NVIDIA NIM Diagnostic")
    print(f"{'='*60}")
    print(f"  APP_BRAIN_MODEL : {provider}")
    print(f"  NVIDIA_BASE_URL : {base_url}")
    print(f"  NVIDIA_MODEL_ID : {model_id}")

    if api_key:
        redacted = api_key[:12] + "..." + api_key[-4:] if len(api_key) > 16 else "***"
    else:
        redacted = "(empty!)"
    print(f"  NVIDIA_API_KEY  : {redacted}")

    if api_key and not api_key.startswith("nvapi-"):
        print(f"\n  ⚠️  KEY FORMAT WARNING: key must start with 'nvapi-' but starts with {api_key[:8]!r}.")
        print("      Edit .env and remove any stray characters before the key value.")
        return

    print()

    if not api_key:
        print("❌  NVIDIA_API_KEY is empty — set it in .env")
        return

    # ── Step 1: List all models via raw HTTP (avoids SDK pagination quirks) ──
    print("Step 1 — Fetching models list...")
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    available_model_ids: list[str] = []

    async with httpx.AsyncClient(timeout=15) as http:
        try:
            r = await http.get(f"{base_url}/models", headers=headers)
            r.raise_for_status()
            data = r.json()
            # OpenAI /models returns {"object": "list", "data": [...]}
            items = data.get("data", data) if isinstance(data, dict) else data
            available_model_ids = [
                m.get("id", m) if isinstance(m, dict) else str(m)
                for m in items
            ]
            if available_model_ids:
                print(f"  ✅  {len(available_model_ids)} model(s) on your account:")
                for mid in sorted(available_model_ids):
                    marker = " ◀ configured" if mid == model_id else ""
                    print(f"      {mid}{marker}")
                if model_id not in available_model_ids:
                    print(f"\n  ⚠️  Configured model '{model_id}' is NOT in this list.")
            else:
                print("  ℹ️  /models returned an empty list (endpoint may not be available for your account).")
        except httpx.HTTPStatusError as e:
            print(f"  ℹ️  /models returned {e.response.status_code} (not always available — continuing).")
        except Exception as e:
            print(f"  ℹ️  Could not fetch /models: {e}")

    # ── Step 2: Probe candidate models ───────────────────────────────────────
    print(f"\nStep 2 — Probing {len(CANDIDATE_MODELS)} candidate models (minimal call each)...")
    client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
    working: list[str] = []

    for mid in CANDIDATE_MODELS:
        try:
            resp = await client.chat.completions.create(
                model=mid,
                messages=[{"role": "user", "content": "Reply OK"}],
                max_tokens=5,
            )
            reply = (resp.choices[0].message.content or "").strip()
            working.append(mid)
            marker = " ◀ configured" if mid == model_id else ""
            print(f"  ✅  {mid}{marker}  →  {reply!r}")
        except openai.NotFoundError:
            print(f"  ✗   {mid}  (not on your account / wrong region)")
        except openai.AuthenticationError:
            print(f"  ✗   {mid}  (auth error — check key)")
        except openai.RateLimitError:
            working.append(mid)  # rate-limited → exists, just busy
            print(f"  ⚠   {mid}  (rate-limited — model exists but busy)")
        except Exception as e:
            print(f"  ?   {mid}  ({type(e).__name__}: {e})")

    # ── Step 3: Structured-output round-trip with configured model ────────────
    print(f"\nStep 3 — Structured-output test with configured model '{model_id}'...")
    if model_id not in working:
        print(f"  ⚠️  Skipping — '{model_id}' did not respond in Step 2.")
        print("      Recommendation: set NVIDIA_MODEL_ID in .env to one of these working models:")
        for m in working:
            print(f"          {m}")
    else:
        schema = _Ping.model_json_schema()
        try:
            resp = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Respond ONLY with a JSON object matching this schema — "
                            "no markdown, no explanation:\n"
                            + json.dumps(schema)
                        ),
                    },
                    {"role": "user", "content": "Ping"},
                ],
                max_tokens=20,
            )
            content = resp.choices[0].message.content or ""
            # Strip optional markdown fences
            content = content.strip()
            if content.startswith("```"):
                nl = content.find("\n")
                content = content[nl + 1:] if nl != -1 else content[3:]
                content = content.rstrip().rstrip("`").rstrip()
            parsed = _Ping.model_validate_json(content)
            print(f"  ✅  Structured output round-trip succeeded: {parsed}")
        except Exception as e:
            print(f"  ❌  {type(e).__name__}: {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if working:
        if model_id in working:
            print(f"✅  Configured model '{model_id}' works — no .env change needed.")
        else:
            print("🔧  Add ONE of these lines to your .env and restart the server:")
            for m in working:
                print(f"        NVIDIA_MODEL_ID={m}")
    else:
        print("❌  No candidate models responded. Check your API key and account access.")
        print("    Browse available models at: https://build.nvidia.com/explore/discover")
    print()


if __name__ == "__main__":
    asyncio.run(main())
