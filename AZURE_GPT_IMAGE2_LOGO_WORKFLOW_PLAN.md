# Azure GPT-Image-2 Logo Batch Workflow Plan

This repository now implements Azure OpenAI GPT-Image-2 as a first-class provider for large one-image-per-prompt logo batches.

The intended default workflow is:

1. Import structured prompts with `prompt_id`, `category_id`, and `prompt`.
2. Apply the Azure Logo Batch preset.
3. Generate missing rows only, using `n=1`, `1024x1024`, medium quality, concurrency `1`, and `4` images/minute.
4. Resume safely after interruption by skipping rows that already have output images.
5. Export deterministic PNGs, `generation_log.jsonl`, metadata, and verification summaries.

The preset appends a logo-only prompt wrapper that asks for one centered flat vector-style logo on a white background, avoids mockups and generic AI clichés, and keeps output suitable for first-pass logo exploration.

Azure configuration is read only from environment variables:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_GPT_IMAGE_2_DEPLOYMENT`
- optional `AZURE_OPENAI_API_VERSION`, default `preview`

Generated images and logs remain outside git-tracked files unless explicitly exported by the user.
