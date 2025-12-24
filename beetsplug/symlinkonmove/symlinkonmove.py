import os
from beets.plugins import BeetsPlugin

class SymlinkOnMove(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.register_listener('import_task_files', self.on_import_task_files)

    def on_import_task_files(self, task, session):
        # Only act on move imports
        if not session.config['move']:
            return
        elif session.config['copy'] or session.config['link']:
            return

        # Album import
        if task.is_album:
            for old, item in zip(task.old_paths, task.items):
                self._create_symlink(old, item.path)
        else:
        # Singleton import
            if task.old_path:
                self._create_symlink(task.old_path, task.item.path)    
    
    def _create_symlink(self, old_path, new_path):
        # If something already exists, do not clobber
        if os.path.exists(old_path):
            self._log.warning("Not creating symlink, path exists: %s", old_path)
            return

        try:
            os.symlink(new_path, old_path)
            self._log.info("Created symlink: %s → %s", old_path, new_path)
        except OSError as exc:
            self._log.error(
                "Failed to create symlink %s → %s: %s",
                old_path,
                new_path,
                exc,
            )
