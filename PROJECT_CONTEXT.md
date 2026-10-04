# Landing development context

## Purpose and architecture
Static landing pages, a separate vacancy page in annaelle-work/, and a Python lead gateway in backend/. The related repositories efilym89/annaelle-taplink and efilym89/annaelle-sales-manager are independent components with their own histories. Use all three repositories when continuing this workspace; do not fold or overwrite their Git boundaries.

## Commands and stopping point
Frontend needs Node and no package installation: node --check script.js; node --check i18n.js; node --check build-tilda.cjs. node build-tilda.cjs regenerates T123 snippets and the marked offers section in i18n.js; run it in a disposable copy when checking clean checkout. Existing snippets reference the original public asset URLs; do not redirect or publish them during environment setup.

Backend requires Python >=3.12: python -m venv .venv; .venv/bin/python -m pip install -e './backend[dev]'. Tests: from backend/, run the virtualenv Python -m pytest -q with runtime credentials cleared and outbound network blocked, while preserving mocked/ASGI transports. Backend tests were not run on the available local Python 3.11. Never use uvicorn, webhook registration or real lead submissions as setup checks.

Related taplink/sales-manager components are static HTML and need no dependency installation. Their Tilda snippets can reference publicly served pages. Development validation must not change main or Pages settings.

## Continuity and boundaries
2026-10-04: a separate development migration branch adds public-safe instructions only. Existing code, assets, Git history and publication branches are preserved. No feature fixes or production changes were made. A GitHub branch is not proof of a published Cloud environment; verify the exact commit and dependency/test results in a fresh task.

Keep private context, credentials, runtime state and personal materials outside public commits. A development checkout of existing raster/history content requires separate privacy review before transfer to a new service. Do not remove original assets automatically. No source-conversation URLs are recorded through supported tools; do not invent links or read internal session stores.
