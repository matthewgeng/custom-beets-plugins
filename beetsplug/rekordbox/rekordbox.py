import json
import os
import re
import sys
import unicodedata

from beets import config, util
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, print_
from beetsplug.info import library_data
from pyrekordbox import MasterDatabase


def nfc(s):
    return unicodedata.normalize("NFC", s)


def sanitize(s):
    """Replace characters that are invalid in filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', s).strip()


USAGE = """usage: beet rekordbox <action>

actions:
  diff       tracks in beets not imported into Rekordbox
  playlist   show which Rekordbox playlists a track belongs to
  export     export library as JSON with Rekordbox playlist membership
             use --dir to write one file per album instead of stdout
"""

ACTIONS = ("diff", "playlist", "export")


class RekordboxDiff(BeetsPlugin):
    def commands(self):
        cmd = Subcommand("rekordbox", help="compare beets library with Rekordbox")
        cmd.parser.add_option(
            "--reverse",
            action="store_true",
            default=False,
            help="(diff) show tracks in Rekordbox not in beets instead",
        )
        cmd.parser.add_option(
            "--dir",
            dest="export_dir",
            metavar="PATH",
            default=None,
            help="(export) write one JSON file per album/singleton to this directory "
                 "(default: beets config dir/library-snapshot)",
        )
        cmd.func = self.rekordbox
        return [cmd]

    def _open_db(self):
        return MasterDatabase()

    def rekordbox(self, lib, opts, args):
        if not args or args[0] not in ACTIONS:
            print_(USAGE)
            return

        action, rest = args[0], args[1:]

        if action == "diff":
            self._diff(lib, opts)
        elif action == "playlist":
            self._playlist(lib, rest)
        elif action == "export":
            self._export(lib, opts, rest)

    # --- actions ---

    def _diff(self, lib, opts):
        self._log.info("Loading Rekordbox database...")
        rb_db = self._open_db()
        rb_keys = {
            (nfc(c.ArtistName or ""), nfc(c.Title or ""))
            for c in rb_db.get_content()
        }

        beets_items = {
            (nfc(item.artist), nfc(item.title)): item
            for item in lib.items()
        }

        if opts.reverse:
            missing = sorted(rb_keys - set(beets_items.keys()))
            print_(f"\n{len(missing)} tracks in Rekordbox not found in beets:\n")
            for artist, title in missing:
                print_(f"{artist} - {title}")
        else:
            missing_keys = sorted(set(beets_items.keys()) - rb_keys)
            missing_items = [beets_items[k] for k in missing_keys]
            print_(f"\n{len(missing_items)} tracks in beets not imported into Rekordbox:\n")
            for item in missing_items:
                print_(f"{item.albumartist or item.artist} - {item.album} - {item.title}")

    def _export(self, lib, opts, args):
        self._log.info("Loading Rekordbox playlists...")
        rb_db = self._open_db()

        path_to_playlists = {}
        for ps in rb_db.get_playlist_songs():
            path = nfc(ps.Content.FolderPath) if ps.Content else None
            name = ps.Playlist.Name if ps.Playlist else None
            if path and name:
                path_to_playlists.setdefault(path, []).append(name)

        # Collect all enriched item dicts
        enriched = []
        for data_emitter in library_data(lib, args):
            try:
                data, item = data_emitter("*")
            except Exception as exc:
                self._log.error("cannot read item: {}", exc)
                continue

            for key, value in data.items():
                if isinstance(value, bytes):
                    data[key] = util.displayable_path(value)

            path = nfc(item.path.decode("utf-8", errors="surrogateescape"))
            data["rekordbox_playlists"] = sorted(path_to_playlists.get(path, []))
            enriched.append((item, data))

        if opts.export_dir is None:
            export_dir = os.path.join(config.config_dir(), "library-snapshot")
        else:
            export_dir = opts.export_dir

        self._export_to_dir(enriched, export_dir)

    def _export_to_dir(self, enriched, export_dir):
        export_dir = os.path.expanduser(export_dir)

        # Group by (albumartist, album). Singletons have no album_id.
        groups = {}
        for item, data in enriched:
            if item.album_id:
                key = ("album", sanitize(item.albumartist or item.artist), sanitize(item.album))
            else:
                key = ("singleton", sanitize(item.artist), sanitize(item.title))
            groups.setdefault(key, []).append(data)

        for key, items in groups.items():
            kind = key[0]
            if kind == "album":
                _, albumartist, album = key
                file_path = os.path.join(export_dir, albumartist, f"{album}.json")
            else:
                _, artist, title = key
                file_path = os.path.join(export_dir, "_singletons", f"{artist} - {title}.json")

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, default=str)
                f.write("\n")
            self._log.info("Wrote {}", file_path)

    def _playlist(self, lib, args):
        if not args:
            print_("usage: beet rekordbox playlist <query>")
            return

        query = " ".join(args)
        items = list(lib.items(query))

        if not items:
            print_(f"No beets tracks found for query: {query}")
            return

        self._log.info("Loading Rekordbox playlists...")
        rb_db = self._open_db()

        # Build path -> playlist names map
        path_to_playlists = {}
        for ps in rb_db.get_playlist_songs():
            path = nfc(ps.Content.FolderPath) if ps.Content else None
            name = ps.Playlist.Name if ps.Playlist else None
            if path and name:
                path_to_playlists.setdefault(path, []).append(name)

        for item in items:
            path = nfc(item.path.decode("utf-8"))
            playlists = path_to_playlists.get(path)
            track_label = f"{item.artist} - {item.title}"
            if playlists:
                print_(f"{track_label}: {', '.join(sorted(playlists))}")
            else:
                print_(f"{track_label}: (not in any playlist)")
