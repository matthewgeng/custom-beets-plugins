import os
from beets.plugins import BeetsPlugin


class SkipAliases(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.register_listener('import_task_created', self.on_import_task_created)

    def on_import_task_created(self, task, session):
        """Remove tasks from the pipeline where all files are symlinks.

        When a listener returns a list from import_task_created, it replaces
        the task in the pipeline. Returning [] drops the task entirely,
        preventing any DB writes or file operations.
        """
        paths = getattr(task, 'paths', None)
        if not paths:
            return  # Sentinel task, leave it alone

        if all(os.path.islink(p) for p in paths):
            self._log.warning(
                'Skipping already-imported symlinks: {}', paths[0]
            )
            return []
