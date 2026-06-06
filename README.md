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
- Providers for mock generation, OpenAI image generation, and Google Gemini image generation.
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
```

Without provider keys, use the mock provider to exercise the UI and queueing flow.

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
