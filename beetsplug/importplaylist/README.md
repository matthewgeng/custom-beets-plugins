# importplaylist (deprecated — use `importsession`)

> **Superseded by `importsession`**, which combines this plugin's functionality with `importlog`. Migrate by replacing `importplaylist` with `importsession` in your config and renaming `output_dir` to `playlist_dir`.

# importplaylist

After each import session, writes an M3U playlist file containing the real beets library paths of every track that was just imported. Import the playlist into Rekordbox (or any other tool) to reference the actual files directly.

## Purpose

After a move import, beets relocates files to the library directory. This plugin captures those final paths and writes a dated M3U so you can immediately import new tracks into Rekordbox without manually hunting for files.

## Usage

Run a normal import:

```bash
beet import --incremental --noautotag --move --set source=bandcamp <path>
```

A playlist file like `2026-04-05T14-32-01.m3u` is written to the configured output directory when the import finishes. Drag it into Rekordbox.

## Config

```yaml
importplaylist:
  output_dir: ~/.config/beets/playlists   # default
```
