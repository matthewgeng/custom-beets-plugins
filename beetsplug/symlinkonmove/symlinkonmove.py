import os
import shutil
from beets import plugins
from beets.plugins import BeetsPlugin

ARTIFACT_EXTENSIONS = {b'.jpg', b'.jpeg', b'.png', b'.gif', b'.tiff', b'.pdf'}

class SymlinkOnMove(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.register_listener('import_task_files', self.on_import_task_files)

    def on_import_task_files(self, task, session):
        # Only act on move imports. Note: don't also check session.config['copy']
        # because beets does NOT reset copy=False when --move is passed on the CLI,
        # so session.config['copy'] can be True even during a move import.
        if not session.config['move'].get(bool):
            return

        # Album import
        if task.is_album:
            for old, item in zip(task.old_paths, task.items):
                self._create_symlink(old, item.path)
            if task.old_paths and task.items:
                self._symlink_artifacts(
                    os.path.dirname(task.old_paths[0]),
                    os.path.dirname(task.items[0].path),
                )
        else:
            # Singleton import — skip artifact symlinking since old_dir is
            # likely a collection folder, not an album-specific directory
            if task.old_path:
                self._create_symlink(task.old_path, task.item.path)

    def _symlink_artifacts(self, old_dir, new_dir):
        """Move image artifacts from old_dir to new_dir, then symlink back."""
        if old_dir == new_dir:
            return

        try:
            old_files = os.listdir(old_dir)
        except OSError as exc:
            self._log.error('Failed to list directory {}: {}', old_dir, exc)
            return

        for filename in old_files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ARTIFACT_EXTENSIONS:
                continue

            old_path = os.path.join(old_dir, filename)
            new_path = os.path.join(new_dir, filename)

            # Skip if already a symlink (already processed)
            if os.path.islink(old_path):
                continue

            # Move the artifact to the library directory
            if os.path.exists(new_path):
                self._log.warning(
                    'Artifact already exists at destination, skipping move: {}',
                    new_path,
                )
            else:
                try:
                    shutil.move(old_path, new_path)
                    self._log.info('Moved artifact: {} -> {}', old_path, new_path)
                    plugins.send('artifact_moved', old_path=old_path, new_path=new_path)
                except OSError as exc:
                    self._log.error(
                        'Failed to move artifact {} -> {}: {}',
                        old_path, new_path, exc,
                    )
                    continue

            # Create symlink at old location pointing to new location
            self._create_symlink(old_path, new_path)

    def _create_symlink(self, old_path, new_path):
        # If something already exists (file or broken symlink), do not clobber
        if os.path.exists(old_path) or os.path.islink(old_path):
            self._log.warning('Not creating symlink, path exists: {}', old_path)
            return

        try:
            os.symlink(new_path, old_path)
            self._log.info('Created symlink: {} -> {}', old_path, new_path)
        except OSError as exc:
            self._log.error(
                'Failed to create symlink {} -> {}: {}',
                old_path,
                new_path,
                exc,
            )
