import os
from datetime import datetime
from beets.plugins import BeetsPlugin


class ImportPlaylist(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add({
            'output_dir': '~/.config/beets/playlists',
        })
        self._paths = []
        self.register_listener('import_begin', self.on_import_begin)
        self.register_listener('import_task_files', self.on_import_task_files)
        self.register_listener('cli_exit', self.on_cli_exit)

    def on_import_begin(self, session):
        self._paths = []

    def on_import_task_files(self, task, session):
        if task.is_album:
            for item in task.items:
                if item and item.path:
                    self._paths.append(item.path.decode('utf-8', errors='surrogateescape'))
        else:
            item = getattr(task, 'item', None)
            if item and item.path:
                self._paths.append(item.path.decode('utf-8', errors='surrogateescape'))

    def on_cli_exit(self, lib):
        if not self._paths:
            return

        output_dir = os.path.expanduser(self.config['output_dir'].get(str))
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        filepath = os.path.join(output_dir, f'{timestamp}.m3u')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for path in self._paths:
                f.write(path + '\n')

        self._log.info('Wrote import playlist: {} ({} tracks)', filepath, len(self._paths))
        self._paths = []
