# ImageAI Batch Generator

ImageAI is a desktop workspace for running large batches of image generation prompts. It is built for pasting many prompts, applying shared generation settings, overriding individual rows, queueing work safely, and exporting the resulting images and metadata.

The app can run fully offline with the mock provider. Real generation providers are optional and are configured with local environment variables that are never committed.

## Features

- Batch prompt input from plain text, numbered lists, JSON arrays, JSON Lines, or CSV.
- Per-row prompt, provider, model, size, count, style, negative prompt, seed, quality, and safety overrides.
- Global generation settings that can be applied to selected rows.
- Queue management with concurrency limits, rate limiting, cancellation, and progress state.
- Session autosave and explicit session open/save controls.
- Image gallery, copy/open/export actions, metadata export, tags, prompt templates, undo/redo, and summary statistics.
- Providers for mock generation, OpenAI image generation, Google Gemini image generation, and Azure OpenAI GPT-Image-2.
- Azure Logo Batch workflow with structured prompt IDs, prompt wrapper preview, quota-safe generate-missing, deterministic filenames, JSONL logs, and verification/export summaries.
- Three UI surfaces:
  - PySide6 desktop UI, launched with `python main.py`.
  - Python JSON-RPC backend for alternate clients.
  - Experimental macOS SwiftUI client in `macos-swiftui/`.

## Requirements

- Python 3.10 or newer.
- macOS is the primary tested desktop target.
- Optional: Swift 5.9 or newer for the SwiftUI client.
- Optional: Node.js 20 or newer for the experimental React/Electron frontend.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` only if you want real provider calls:

```bash
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_GPT_IMAGE_2_DEPLOYMENT=your-gpt-image-2-deployment-name
AZURE_OPENAI_API_VERSION=preview
```

Without provider keys, use the mock provider to exercise the UI and queueing flow.

## Azure GPT-Image-2 Logo Batch Workflow

Use the React/Electron sidebar's **Azure Logo Batch** panel, or the PySide **Azure Logo Preset** button, for large logo exploration runs.

Default preset values:

- Provider/model: Azure OpenAI GPT-Image-2 deployment.
- Size: `1024x1024`.
- Quality: medium.
- Images per prompt: `n=1`.
- Output format: PNG.
- Throttle: 4 images/minute, concurrency 1.

Structured CSV imports should include:

```csv
prompt_id,category_id,prompt
prompt0001,cat01,"Design a minimal logo for inAi..."
prompt0002,cat01,"Design a different minimal logo for inAi..."
```

Azure logo outputs are saved with deterministic filenames such as:

```text
cat01_prompt0001_q-medium_run01.png
```

Each session writes `generation_log.jsonl` with prompt IDs, category IDs, full prompts sent to Azure, filenames, statuses, Azure request IDs, and errors. Export also includes `export_metadata.json`, `export_summary.json`, and the generation log when present.

### Prepare Markdown Logo Prompts

Use `scripts/prepare_logo_prompts.py` when logo prompts start as category-organized Markdown files and need to become import-ready ImageAI batches.

```bash
python scripts/prepare_logo_prompts.py --source /path/to/logo-markdown-folder
```

By default, outputs are written to `/path/to/logo-markdown-folder/logos_prepared`. Use `--output` to choose another destination:

```bash
python scripts/prepare_logo_prompts.py \
  --source /path/to/logo-markdown-folder \
  --output /path/to/prepared-output
```

The script extracts prompt headings such as `## N01 - Missing core`, `## C01 — Kernel in a vault`, `## 61. AI kernel inside a shell`, and `### 15.01 — Source ledger`. It writes:

- `logos_prompts.csv`: structured CSV with `prompt_id`, `category_id`, and `prompt`.
- `logos_prompts.json` and `logos_prompts.jsonl`: structured manifests.
- `imageai_session.json`: an ImageAI session preserving prompt/category IDs and source metadata.
- `per_category/*.csv`: one CSV per category.
- `summary.json` and `preparation_report.md`: preparation counts and source summary.

The generated session uses relative source paths in metadata so prepared files are publishable without exposing local machine paths.

## Run The PySide App

```bash
python main.py
```

The app stores autosaved session data under `~/.imagen/`.

## Run The Backend

The backend is used by the SwiftUI and React clients:

```bash
python -m app.backend_server
```

It listens on `127.0.0.1:8765` by default.

## Run The SwiftUI Client

```bash
cd macos-swiftui
swift run ImagenNative
```

The SwiftUI app starts the Python backend automatically when it is not already running.

## Run The React/Electron Client

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the Python backend at `http://127.0.0.1:8765`.

## Repository Layout

```text
app/                    Python backend, providers, queue, session, export, and PySide UI
frontend/               Experimental React/Electron client
macos-swiftui/          Experimental native macOS SwiftUI client
scripts/                Utility scripts for preparing prompt batches
tests/                  Python unit tests for parser, queue, session, exporter, and related logic
main.py                 PySide desktop entrypoint
requirements.txt        Python dependencies
```

## Tests

```bash
pytest
```

The default test suite does not require provider credentials.

## Security

Do not commit `.env`, generated images, local sessions, provider credentials, or exported customer/user data. See `SECURITY.md` for reporting and handling guidance.
