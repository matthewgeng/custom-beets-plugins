# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment & Commands

This project uses **uv** for dependency management and **mise** for toolchain management (Python 3.12).

```bash
# Install dependencies
uv sync

# Run the main script
uv run python main.py

# Install plugins into a local beets config for testing
uv run beet import <path>
```

Set `BEETS_SOURCE` environment variable before importing to specify the music source:
```bash
BEETS_SOURCE=bandcamp uv run beet import <path>
```

## Architecture

This repo contains custom [beets](https://beets.io) plugins, located under `beetsplug/`. Each plugin is a subdirectory with a single Python file, following the beets plugin convention where the directory and module share the same name.

beets documentation is here; https://beets.readthedocs.io/en/stable/
and the beets github is here: https://github.com/beetbox/beets

### Plugin conventions

Every plugin must have:
- **`README.md`** in its directory documenting purpose, usage, config options, and how to run tests
- **`test_<name>.py`** in its directory with unit tests (run via `uv run pytest beetsplug/<name>/`)

Tests use `unittest.TestCase` with mocked beets internals (patch `BeetsPlugin.__init__` and `register_listener`). See `beetsplug/importsession/test_importsession.py` for the established pattern. The beets test helpers (`beets.test.helper`) require the beets source tree and are not suitable for use with the installed package.

### Plugins

**`beetsplug/sourcemetadata/sourcemetadata.py`** — `SourceMetadata` plugin
- Adds a custom `source` field to the beets library DB and writes it as a file tag (currently only FLAC supported via mutagen)
- Source is resolved from `BEETS_SOURCE` env var, falling back to `default_source` config key
- Valid sources are configurable via `valid_sources` config key (default: `bandcamp`, `soundcloud`, `tidal`, `unknown`)
- Uses an import stage (`imported`) that runs for all imports including use-as-is
- `on_import_begin` listener stores the resolved source on the session object; `imported` stage reads it back and applies to each item

**`beetsplug/symlinkonmove/symlinkonmove.py`** — `SymlinkOnMove` plugin
- After a move import, creates a symlink at the original file path pointing to the new location
- Only activates when `move=true` and neither `copy` nor `link` are set in the beets config
- Handles both album and singleton imports

**`beetsplug/skipaliases/skipaliases.py`** — `SkipAliases` plugin
- Skips import tasks where every file is a symlink, preventing re-import of symlinks left by `symlinkonmove`

**`beetsplug/importsession/importsession.py`** — `ImportSession` plugin
- Tracks each import session and writes a timestamped M3U playlist of imported library paths
- For move imports, also writes a JSON session log with original/library path pairs supporting undo via `beet importsession --undo <id>`
- Consolidates the deprecated `importlog` and `importplaylist` plugins

**`beetsplug/importlog/importlog.py`** — `ImportLog` plugin *(deprecated, use `importsession`)*

**`beetsplug/importplaylist/importplaylist.py`** — `ImportPlaylist` plugin *(deprecated, use `importsession`)*

**`beetsplug/rekordbox/rekordbox.py`** — `RekordboxDiff` plugin
- `beet rekordbox diff` — shows tracks in beets not imported into Rekordbox
- `beet rekordbox playlist <query>` — shows which Rekordbox playlists a track belongs to
- `beet rekordbox export [--dir]` — exports library as JSON annotated with Rekordbox playlist membership

### Key beets Concepts Used

- `BeetsPlugin` base class from `beets.plugins`
- `import_stages` list: pipeline stages that run during import (including use-as-is)
- `register_listener`: event hooks (e.g. `import_begin`, `import_task_files`)
- `MediaField` + `StorageStyle` from `mediafile`: custom audio file tag definitions
- `Item._types` / `Item._fields`: registering custom DB fields on the beets Item model
- `ImportTask` / `ImportSession`: task and session objects passed through the import pipeline

### Beets Plugin Config

Plugins are referenced by directory name in `~/.config/beets/config.yaml`:
```yaml
plugins:
  - sourcemetadata
  - symlinkonmove

sourcemetadata:
  default_source: bandcamp
  valid_sources:
    - bandcamp
    - soundcloud
    - tidal
    - unknown
```
