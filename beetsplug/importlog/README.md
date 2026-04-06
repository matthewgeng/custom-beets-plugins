# importlog (deprecated — use `importsession`)

> **Superseded by `importsession`**, which combines this plugin's functionality with `importplaylist`. Migrate by replacing `importlog` with `importsession` in your config.

# importlog

Logs each import session to a JSON file and supports undoing past imports — moving files back to their original locations and removing them from the beets library.

## Usage

```bash
# List all logged import sessions
beet importlog

# Undo a specific session by ID
beet importlog --undo 2026-04-05T14:32:01
```

Session IDs are timestamps in `YYYY-MM-DDTHH:MM:SS` format, shown by `beet importlog`.

Undo will:
1. Remove the symlink at the original path (if present)
2. Move the file back from the library to its original location
3. Remove the item from the beets database
4. Restore any artifacts (cover art, etc.) that were moved

## Config

```yaml
importlog:
  logfile: ~/.config/beets/import-log.json   # default
```

Only move imports are logged. Copy and link imports are ignored.
