# rekordbox

Compares the beets library against Rekordbox and exports library data enriched with Rekordbox playlist membership.

Requires [`pyrekordbox`](https://pyrekordbox.readthedocs.io/) and access to the Rekordbox master database.

## Commands

```bash
beet rekordbox diff
```
Lists tracks in beets that have not been imported into Rekordbox (matched by artist + title).

```bash
beet rekordbox diff --reverse
```
Lists tracks in Rekordbox that are not in beets.

```bash
beet rekordbox playlist <query>
```
Shows which Rekordbox playlists a beets track belongs to. Accepts any beets query.

```bash
beet rekordbox export [--dir <path>]
```
Exports the full beets library as JSON, with each track annotated with its Rekordbox title and playlist membership. Files are written one per album (or singleton) under the given directory, defaulting to `~/.config/beets/library-snapshot/`.

## Notes

- Rekordbox paths are resolved through symlinks so alias paths match real library paths during export.
- Album files are grouped by albumartist and album name; singletons go under `_singletons/`.
