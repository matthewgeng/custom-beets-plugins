# importsession

Tracks each import session and produces two outputs:

1. **M3U playlist** — a timestamped playlist of every track's real library path, written after every import. Drag into Rekordbox (or any tool) to reference the actual files.
2. **JSON session log** — a persistent log of move imports with original and library paths, supporting undo via `beet importsession --undo`.

Consolidates the functionality of the deprecated `importlog` and `importplaylist` plugins.

## Usage

Run a normal import — the playlist and log are written automatically on exit:

```bash
beet import --incremental --noautotag --move --set source=bandcamp <path>
```

List past sessions:

```bash
beet importsession
```

Undo a session (moves files back, removes from DB):

```bash
beet importsession --undo 2026-04-05T14:32:01
```

## Config

```yaml
importsession:
  playlist_dir: ~/.config/beets/playlists   # set to null to disable
  logfile: ~/.config/beets/import-log.json  # set to null to disable
```

## Behaviour notes

- The playlist is written for **all** import types (move, copy, link).
- The session log is only written for **move** imports — original paths are needed for undo to make sense.
- Each playlist file is named by timestamp, e.g. `2026-04-05T14-32-01.m3u`.

## Tests

```bash
uv run pytest beetsplug/importsession/
```
