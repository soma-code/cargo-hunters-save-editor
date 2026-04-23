# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this is

A single-file offline save editor for the Steam game **Cargo Hunters** (by OrderOfMeta). It reads and writes `offline.save` (JSON), presents a visual grid inventory editor, and lets users spawn/delete/move items, edit account stats, skills, currency, and counters.

No external Python dependencies are required to run `editor.py` — only `tkinter` (stdlib). `UnityPy` is an optional dev dependency used only to re-extract game data.

---

## Running

```bash
python editor.py
```

Auto-loads from `%LOCALAPPDATA%/../LocalLow/OrderOfMeta/Cargo Hunters/offline.save`.

---

## Architecture

Everything lives in `editor.py`. There is no test suite, no build step, and no package structure.

**Key classes:**
- `SaveEditor(tk.Tk)` — root window; owns `self.data` (the parsed save dict) and `self.items_db` (the item template lookup). Builds all tabs and handles load/save.
- `StashGrid(ttk.Frame)` — the canvas-based inventory grid. Owns `_grid_items {(row,col): item}` and `_item_cells {item_id: [(row,col),...]}`. Handles drag/drop, right-click spawn/delete, and drawing.
- `SpawnDialog(tk.Toplevel)` — searchable item browser. Reads from `items_db`, calls `StashGrid.spawn_item()`.

**Key data files:**
- `item_templates.json` — extracted from the game bundle; contains every item's ID, internal name, size, category, price, stack cap, condition info.
- `item_names_en.json` — extracted from the game's localization bundle (`localization-stringtables_assets_all.bundle`); maps `TableEntryReference` IDs to English display names. Used to replace internal names like `AssaultRifle_05` with in-game names like `SK99AA`.

**Item name resolution** (`_load_items_db`): internal `Name` (component `$t=26276`) is the fallback. If the item has a `LocalizedName.TableEntryReference` in component `$t=4373`, look it up in `item_names_en`. Skip if the resolved string contains `{` (unresolved localization link — the internal name is cleaner in those cases, e.g. ammo).

**Grid coordinate system:** `J` = row (vertical), `I` = column (horizontal). Items without a `J` in their save position (e.g. top-slot containers like the stash bag itself) default to `J=0`. The playable grid is 8 columns × 30 rows (`GRID_COLS`, `GRID_ROWS`). Top 4 rows (J=0–3) are occupied by the stash containers; the free grid starts at J=4.

**Stash container discovery** (`_find_stash_container_id`): the save has a root inventory item → one child container → items with J/I positions. The function finds the child whose direct children have J positions.

**Extracting game data** (dev only, requires `pip install unitypy`):
```bash
# item templates
python -c "from pathlib import Path; from editor import _extract_items_db; _extract_items_db(Path('item_templates.json'))"

# english names
python -c "from pathlib import Path; from editor import _extract_names_en; _extract_names_en(Path('item_names_en.json'))"
```

Both functions find the game bundle automatically via the Steam registry + `libraryfolders.vdf`.

---

## Before any commit or push

**Always scan for personal information before committing.** This repo is public. Check every changed file for:
- Usernames, real names, email addresses
- Local machine paths (`ATLAS`, `AppData`, `SteamLibrary`, `C:\Users\...`)
- Save file contents or fragments (save files contain account IDs)

Quick scan:
```bash
git diff HEAD --name-only | xargs grep -iE "ATLAS|AppData|SteamLibrary|@[a-z]" 2>/dev/null
```

`item_names_en.json` is extracted from the game's localization bundle — it contains only game strings, no personal data, but verify after any regeneration.

---

## Release workflow

**NEVER run PyInstaller from the global Python.** It has UnityPy, PyTorch, TensorFlow and many other packages installed globally, which produces a massively bloated exe. A clean `.venv` lives in the project root with only `pyinstaller` installed. Use it. If it's been deleted, recreate it:

```bash
python -m venv .venv
.venv/Scripts/pip install pyinstaller
```

The correct release process:

1. **Test** — run `python editor.py` and manually verify changes against a save file
2. **Validate** — confirm the editor loads, stash grid renders correctly, no console errors
3. **Build binary locally** using the clean venv:
   ```bash
   .venv/Scripts/pyinstaller --onefile --windowed --name "CargoHuntersSaveEditor" --add-data "item_templates.json;." --add-data "item_names_en.json;." --distpath dist editor.py
   ```
4. **Test the exe** — run `dist/CargoHuntersSaveEditor.exe` and verify it works
5. **VirusTotal** — upload `dist/CargoHuntersSaveEditor.exe`, confirm clean
6. **Commit** all changes including `item_names_en.json` if regenerated
7. **Tag and push** to trigger GitHub Actions (which rebuilds the final release binary):
   ```bash
   git tag v0.X.0
   git push origin main
   git push origin v0.X.0
   ```
5. **GitHub Actions** (`.github/workflows/build.yml`) builds on a clean `windows-latest` runner with **only `pyinstaller` installed** — no UnityPy, no bloat. Bundles `item_templates.json` and `item_names_en.json`. Attaches the exe to the GitHub release with SHA256.
6. **VirusTotal** — manually upload the released exe, add the scan URL to the release notes.

The current version is tracked via git tags (`git tag --sort=-v:refname`).
