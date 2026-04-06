import json
import os
import shutil
from datetime import datetime

from beets import ui
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, print_


class ImportSession(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self.config.add({
            'logfile': '~/.config/beets/import-log.json',
            'playlist_dir': '~/.config/beets/playlists',
        })
        self._session = None
        self._paths = []
        self.register_listener('import_begin', self.on_import_begin)
        self.register_listener('import_task_files', self.on_import_task_files)
        self.register_listener('artifact_moved', self.on_artifact_moved)
        self.register_listener('cli_exit', self.on_cli_exit)

    def commands(self):
        cmd = Subcommand('importsession', help='List or undo past import sessions')
        cmd.parser.add_option(
            '-u', '--undo',
            dest='undo_id',
            metavar='ID',
            help='undo the import session with this ID',
        )
        cmd.func = self.importsession_command
        return [cmd]

    # ------------------------------------------------------------------ Events

    def on_import_begin(self, session):
        self._session = {
            'id': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'source': getattr(session, 'source', None),
            'actions': [],
            'artifacts': [],
        }
        self._paths = []

    def on_import_task_files(self, task, session):
        if not self._session:
            return

        is_move = session.config['move'].get(bool)

        if task.is_album:
            for item in task.items:
                if item and item.path:
                    self._paths.append(item.path.decode('utf-8', errors='surrogateescape'))
            if is_move:
                for old_path, item in zip(task.old_paths, task.items):
                    self._record(old_path, item)
        else:
            item = getattr(task, 'item', None)
            if item and item.path:
                self._paths.append(item.path.decode('utf-8', errors='surrogateescape'))
            if is_move and getattr(task, 'old_path', None):
                self._record(task.old_path, task.item)

    def on_artifact_moved(self, old_path, new_path):
        if not self._session:
            return
        self._session['artifacts'].append({
            'original_path': old_path.decode('utf-8', errors='surrogateescape'),
            'library_path': new_path.decode('utf-8', errors='surrogateescape'),
        })

    def on_cli_exit(self, lib):
        if not self._session:
            return
        self._write_playlist()
        self._write_log()
        self._session = None
        self._paths = []

    # ----------------------------------------------------------------- Command

    def importsession_command(self, lib, opts, args):
        if opts.undo_id:
            self._undo(lib, opts.undo_id)
        else:
            self._list()

    def _list(self):
        sessions = self._read_log()
        if not sessions:
            print_('No import sessions logged.')
            return
        for s in reversed(sessions):
            source = s.get('source') or 'unknown'
            count = len(s['actions'])
            print_(f"{s['id']}  source={source}  {count} item(s)")

    def _undo(self, lib, session_id):
        sessions = self._read_log()
        session = next((s for s in sessions if s['id'] == session_id), None)
        if not session:
            raise ui.UserError(f'No session found with ID: {session_id}')

        for action in session['actions']:
            original = action['original_path']
            library = action['library_path']
            item_id = action['item_id']

            if os.path.islink(original):
                os.remove(original)
            elif os.path.exists(original):
                self._log.warning('Original path is not a symlink, skipping: {}', original)
                continue

            try:
                os.makedirs(os.path.dirname(original), exist_ok=True)
                shutil.move(library, original)
                self._log.info('Restored: {} -> {}', library, original)
            except OSError as exc:
                self._log.error('Failed to restore {} -> {}: {}', library, original, exc)
                continue

            item = lib.get_item(item_id)
            if item:
                item.remove()

        for artifact in session.get('artifacts', []):
            original = artifact['original_path']
            library = artifact['library_path']

            if os.path.islink(original):
                os.remove(original)
            elif os.path.exists(original):
                self._log.warning('Artifact original path is not a symlink, skipping: {}', original)
                continue

            try:
                shutil.move(library, original)
                self._log.info('Restored artifact: {} -> {}', library, original)
            except OSError as exc:
                self._log.error('Failed to restore artifact {} -> {}: {}', library, original, exc)

        self._save_log([s for s in sessions if s['id'] != session_id])
        print_(f'Undid import session {session_id}.')

    # ------------------------------------------------------------------ Helpers

    def _record(self, old_path, item):
        self._session['actions'].append({
            'item_id': item.id,
            'original_path': old_path.decode('utf-8', errors='surrogateescape'),
            'library_path': item.path.decode('utf-8', errors='surrogateescape'),
        })

    def _write_playlist(self):
        if not self._paths:
            return

        playlist_dir = self.config['playlist_dir'].get()
        if playlist_dir is None:
            return
        playlist_dir = os.path.expanduser(str(playlist_dir))
        os.makedirs(playlist_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        filepath = os.path.join(playlist_dir, f'{timestamp}.m3u')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for path in self._paths:
                f.write(path + '\n')

        self._log.info('Wrote import playlist: {} ({} tracks)', filepath, len(self._paths))

    def _write_log(self):
        if not self._session or not self._session['actions']:
            return

        logfile = self.config['logfile'].get()
        if logfile is None:
            return
        logfile = os.path.expanduser(str(logfile))

        sessions = self._read_log()
        sessions.append(self._session)
        self._save_log(sessions)
        self._log.info('Logged import session {}', self._session['id'])

    def _logfile_path(self):
        logfile = self.config['logfile'].get()
        if logfile is None:
            return None
        return os.path.expanduser(str(logfile))

    def _read_log(self):
        path = self._logfile_path()
        if not path or not os.path.exists(path):
            return []
        with open(path) as f:
            return json.load(f)

    def _save_log(self, sessions):
        path = self._logfile_path()
        if not path:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(sessions, f, indent=2)
