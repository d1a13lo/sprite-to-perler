# Sprite to Perler — documentation

| File / folder | What it is |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | The illustrated user guide (the single source of all written instructions). |
| `Sprite-to-Perler-User-Guide.pdf` | The same guide as a printable PDF, generated from `USER_GUIDE.md`. |
| [images/](images/) | Screenshots of the real Windows program (with numbered callouts) and sample charts. |
| [promo/](promo/) | Before-and-after images for a download page. |
| [examples/](examples/) | Original example sprites made for this documentation (free of third-party artwork). |
| [sample-output/](sample-output/) | Real files exported by the program for the "Pip" example. |
| `tools/` | Scripts that rebuild everything below. |

## Rebuilding (maintainers)

Run from the project folder, after building `dist\Sprite to Perler\` (see the main
[README](../README.md#building-from-source)):

```
.venv\Scripts\python.exe docs\tools\make_examples.py
powershell -ExecutionPolicy Bypass -File docs\tools\capture_screens.ps1
.venv\Scripts\python.exe docs\tools\annotate.py
.venv\Scripts\python.exe docs\tools\make_promos.py
.venv\Scripts\python.exe docs\tools\build_pdf.py
.venv\Scripts\python.exe docs\tools\check_docs.py
```

`capture_screens.ps1` drives the real program through Windows UI Automation (no mouse or
keyboard input), keeps its window behind other windows, and saves demo exports to
`C:\SpriteToPerlerDocs` (a neutral path, so no personal folders appear in screenshots).
Remove that folder afterwards.
