from beets import config
from beets.plugins import BeetsPlugin
from beets.ui import UserError
from beets.library import Item
from beets.dbcore import types
from mediafile import MediaField, MP3DescStorageStyle, StorageStyle
from beets.importer import ImportTask, ImportSession


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

        self.config.add(
            {
                "default_source": None,
                "valid_sources": ["bandcamp", "soundcloud", "tidal", "qobuz", "unknown"]
            })

        self.import_stages = [self.imported]

        self.register_listener("import_begin", self.on_import_begin)

    def on_import_begin(self, session):
        """
        Runs for *all* imports, including use-as-is.
        Resolve source from --set flag or default_source config.
        """
        session.source = self._resolve_source()
        if session.source:
            self._log.info(f"Using source '{session.source}' for import")

    def imported(self, session: ImportSession, task: ImportTask):
        """
        Runs for all imports, including use-as-is.
        Apply source to all items in task.
        """
        session_source = getattr(session, "source", None)

        for item in task.items:
            if session_source:
                # Source provided via --set, apply it and write to file
                if item.source and item.source != session_source:
                    self._log.warning(
                        f"Overriding existing source '{item.source}' "
                        f"with '{session_source}' for {item.path}"
                    )
                item.source = session_source
                item.store()
                item.write()
            elif item.source:
                # Source already embedded in the file tag, use it as-is
                self._log.info(
                    f"Using stored source '{item.source}' for {item.path}"
                )
            else:
                self._log.warning(
                    f"No source for {item.path}. "
                    "Use 'beet import --set source=<value>' or configure default_source."
                )

    def _resolve_source(self):
        set_fields = config["import"]["set_fields"].get(dict) or {}
        src = set_fields.get("source") or self.config["default_source"].get()

        if not src or not src.strip():
            return None

        valid = self.config["valid_sources"].get()
        if valid and src not in valid:
            raise UserError(
                f"Invalid source '{src}'. "
                f"Valid sources are: {', '.join(valid)}"
            )

        return src
