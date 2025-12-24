import os
from beets.plugins import BeetsPlugin
from beets.ui import UserError
from beets.library import Item
from beets.dbcore import types
from mediafile import MediaField, MP3DescStorageStyle, StorageStyle

class SourceMetadata(BeetsPlugin):
    def __init__(self):
        super().__init__()

        field = MediaField(
            MP3DescStorageStyle("source"),
            StorageStyle("source")
        )
        self.add_media_field("source", field)

        if not hasattr(Item, 'source'): 
            Item._types['source'] = types.STRING 
            
        # add default plugin configuration 
        self.config.add(
            { 
                "default_source": None, 
                "valid_sources": ["bandcamp", "soundcloud", "tidal", "unknown"] 
            })

        # Hooks that ALWAYS run (including use-as-is)
        self.register_listener("import_task_start", self.on_task_start)
        self.register_listener("import_task_files", self.on_import_task_files)

    def on_task_start(self, task, session):
        """
        Runs for *all* imports, including use-as-is.
        Resolve and validate source once per task.
        """
        task.source = self._resolve_source()

        self._log.warning(
            f"Using source '{task.source}' for import task" 
        )

    def on_import_task_files(self, task, session):
        src = getattr(task, "source", None)
        if not src:
            return

        # --- Apply source to items (DB + file tags) ---
        for item in task.items:
            # DB
            item.source = src
            item.store()

            # FILE TAG (explicit override of use-as-is)
            item["source"] = src
            item.write()

            self._log.warning(
                f"Applied source '{src}' to {item.path}"
            )
    
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
