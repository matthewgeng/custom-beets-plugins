import os
from beets.plugins import BeetsPlugin
from beets.ui import UserError
from beets.library import Item
from beets.dbcore import types
from mediafile import MediaField, MP3DescStorageStyle, StorageStyle
from beets.importer import ImportTask, ImportSession
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.oggvorbis import OggVorbis

class SourceMetadata(BeetsPlugin):
    def __init__(self):
        super().__init__()

        field = MediaField(
            MP3DescStorageStyle("source"),
            StorageStyle("source")
        )
        self.add_media_field("source", field)

        Item._types['source'] = types.STRING 
        Item._fields['source'] = types.STRING
            
        # add default plugin configuration 
        self.config.add(
            { 
                "default_source": None, 
                "valid_sources": ["bandcamp", "soundcloud", "tidal", "unknown"] 
            })

        self.import_stages = [self.imported]

        # Hooks that ALWAYS run (including use-as-is)
        self.register_listener("import_begin", self.on_import_begin)
        # self.register_listener("import_task_files", self.on_import_task_files)
        # self.register_listener("item_imported", self.on_item_imported)
    
    def on_import_begin(self, session):
        """
        Runs for *all* imports, including use-as-is.
        Resolve and validate source once per task.
        """
        session.source = self._resolve_source()

        self._log.warning(
            f"Using source '{session.source}' for import task" 
        )

    def imported(self, session: ImportSession, task: ImportTask):
        """
        Runs for all imports, including use-as-is.
        Resolve and validate source once per task.
        Apply source to all items in task.
        """
        source = getattr(session, "source", None)
        if not source:
            self._log.error(f"no source on task")
            return

        # --- Apply source to items (DB + file tags) ---
        for item in task.items:
            # DB
            item.source = source
            item.store()

            # File metadata
            file_path = item.path.decode("utf-8")
            self.write_source_tag(file_path, source)

    def _resolve_source(self):
        src = os.environ.get("BEETS_SOURCE") or self.config["default_source"].get()

        if not src or not src.strip():
            raise UserError(
                "No source specified. "
                "Set BEETS_SOURCE or configure default_source."
            )

        valid = self.config["valid_sources"].get()
        if valid and src not in valid:
            raise UserError(
                f"Invalid source '{src}'. "
                f"Valid sources are: {', '.join(valid)}"
            )

        return src

    def write_source_tag(self, file_path: str, source: str):
        """
        Writes a custom 'source' tag to any supported audio file type
        without touching existing metadata.
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            filename = os.path.basename(file_path)
            if ext == ".flac":
                audio = FLAC(file_path)
                audio["source"] = source
                audio.save()
                self._log.info(f"Applied source '{source}' to {file_path}")
                self._log.warning(f"Applied source '{source}' to {filename}")
            else:
                self._log.error(f"Unsupported file type for {filename}")
        except Exception as e:
            self._log.error(f"Error writing source tag to {file_path}: {e}")