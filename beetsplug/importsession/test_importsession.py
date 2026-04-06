import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers for building plugin, task and session mocks
# ---------------------------------------------------------------------------

def make_plugin(tmp_path, playlist_dir=True, logfile=True):
    """Instantiate ImportSession with beets internals mocked out."""
    with patch('beets.plugins.BeetsPlugin.__init__', return_value=None), \
         patch('beets.plugins.BeetsPlugin.register_listener'):
        from beetsplug.importsession.importsession import ImportSession
        plugin = ImportSession.__new__(ImportSession)

    def _config_item(value):
        m = MagicMock()
        m.get = MagicMock(return_value=value)
        return m

    cfg = MagicMock()
    cfg.__getitem__ = MagicMock(side_effect=lambda key: {
        'logfile': _config_item(str(tmp_path / 'import-log.json') if logfile else None),
        'playlist_dir': _config_item(str(tmp_path / 'playlists') if playlist_dir else None),
    }.get(key, _config_item(None)))

    plugin.config = cfg
    plugin._log = MagicMock()
    plugin._session = None
    plugin._paths = []
    return plugin


def make_beets_session(is_move=True, source='bandcamp'):
    session = MagicMock()
    session.config.__getitem__ = MagicMock(
        side_effect=lambda key: MagicMock(
            get=MagicMock(return_value=(is_move if key == 'move' else False))
        )
    )
    session.source = source
    return session


def make_item(library_path, item_id=1):
    item = MagicMock()
    item.path = library_path.encode()
    item.id = item_id
    return item


def make_album_task(items, old_paths):
    task = MagicMock()
    task.is_album = True
    task.items = items
    task.old_paths = [p.encode() for p in old_paths]
    return task


def make_singleton_task(item, old_path):
    task = MagicMock()
    task.is_album = False
    task.item = item
    task.old_path = old_path.encode()
    return task


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestOnImportBegin(unittest.TestCase):
    def setUp(self):
        self.plugin = make_plugin(Path('/tmp'))

    def test_resets_paths(self):
        self.plugin._paths = ['/some/old/path.flac']
        self.plugin.on_import_begin(make_beets_session())
        self.assertEqual(self.plugin._paths, [])

    def test_creates_session_dict(self):
        self.plugin.on_import_begin(make_beets_session(source='bandcamp'))
        self.assertIsNotNone(self.plugin._session)
        self.assertEqual(self.plugin._session['source'], 'bandcamp')
        self.assertEqual(self.plugin._session['actions'], [])
        self.assertEqual(self.plugin._session['artifacts'], [])


class TestOnImportTaskFiles(unittest.TestCase):
    def setUp(self):
        self.plugin = make_plugin(Path('/tmp'))
        self.plugin.on_import_begin(make_beets_session())

    def test_album_move_collects_paths_and_records_actions(self):
        items = [make_item('/lib/Artist/Album/track1.flac', 1),
                 make_item('/lib/Artist/Album/track2.flac', 2)]
        task = make_album_task(items, ['/src/track1.flac', '/src/track2.flac'])

        self.plugin.on_import_task_files(task, make_beets_session(is_move=True))

        self.assertEqual(len(self.plugin._paths), 2)
        self.assertIn('/lib/Artist/Album/track1.flac', self.plugin._paths)
        self.assertEqual(len(self.plugin._session['actions']), 2)

    def test_album_copy_collects_paths_but_no_actions(self):
        items = [make_item('/lib/Artist/Album/track1.flac', 1)]
        task = make_album_task(items, ['/src/track1.flac'])

        self.plugin.on_import_task_files(task, make_beets_session(is_move=False))

        self.assertEqual(len(self.plugin._paths), 1)
        self.assertEqual(len(self.plugin._session['actions']), 0)

    def test_singleton_move_collects_path_and_records_action(self):
        item = make_item('/lib/singletons/track.flac', 1)
        task = make_singleton_task(item, '/src/track.flac')

        self.plugin.on_import_task_files(task, make_beets_session(is_move=True))

        self.assertEqual(self.plugin._paths, ['/lib/singletons/track.flac'])
        self.assertEqual(len(self.plugin._session['actions']), 1)
        action = self.plugin._session['actions'][0]
        self.assertEqual(action['original_path'], '/src/track.flac')
        self.assertEqual(action['library_path'], '/lib/singletons/track.flac')

    def test_action_records_original_and_library_paths(self):
        items = [make_item('/lib/Artist/Album/track1.flac', 42)]
        task = make_album_task(items, ['/original/track1.flac'])

        self.plugin.on_import_task_files(task, make_beets_session(is_move=True))

        action = self.plugin._session['actions'][0]
        self.assertEqual(action['item_id'], 42)
        self.assertEqual(action['original_path'], '/original/track1.flac')
        self.assertEqual(action['library_path'], '/lib/Artist/Album/track1.flac')


class TestWritePlaylist(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.plugin = make_plugin(self.tmp)
        self.plugin.on_import_begin(make_beets_session())

    def test_writes_m3u_with_correct_content(self):
        self.plugin._paths = ['/lib/A/B/track1.flac', '/lib/A/B/track2.flac']
        self.plugin._write_playlist()

        playlists = list((self.tmp / 'playlists').glob('*.m3u'))
        self.assertEqual(len(playlists), 1)

        lines = playlists[0].read_text().splitlines()
        self.assertEqual(lines[0], '#EXTM3U')
        self.assertIn('/lib/A/B/track1.flac', lines)
        self.assertIn('/lib/A/B/track2.flac', lines)

    def test_skips_when_no_paths(self):
        self.plugin._paths = []
        self.plugin._write_playlist()
        self.assertFalse((self.tmp / 'playlists').exists())

    def test_skips_when_playlist_dir_disabled(self):
        plugin = make_plugin(self.tmp, playlist_dir=False)
        plugin._paths = ['/lib/track.flac']
        plugin._write_playlist()
        self.assertFalse((self.tmp / 'playlists').exists())


class TestWriteLog(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.plugin = make_plugin(self.tmp)
        self.plugin.on_import_begin(make_beets_session())

    def _add_action(self, original='/src/t.flac', library='/lib/t.flac', item_id=1):
        self.plugin._session['actions'].append({
            'item_id': item_id,
            'original_path': original,
            'library_path': library,
        })

    def test_writes_json_with_session_data(self):
        self._add_action()
        self.plugin._write_log()

        logfile = self.tmp / 'import-log.json'
        self.assertTrue(logfile.exists())
        sessions = json.loads(logfile.read_text())
        self.assertEqual(len(sessions), 1)
        self.assertEqual(len(sessions[0]['actions']), 1)

    def test_skips_when_no_actions(self):
        self.plugin._write_log()
        self.assertFalse((self.tmp / 'import-log.json').exists())

    def test_skips_when_logfile_disabled(self):
        plugin = make_plugin(self.tmp, logfile=False)
        plugin.on_import_begin(make_beets_session())
        plugin._session['actions'].append({'item_id': 1, 'original_path': '/a', 'library_path': '/b'})
        plugin._write_log()
        self.assertFalse((self.tmp / 'import-log.json').exists())

    def test_appends_across_multiple_sessions(self):
        self._add_action('/src/1.flac', '/lib/1.flac', item_id=1)
        self.plugin._write_log()

        self.plugin.on_import_begin(make_beets_session())
        self._add_action('/src/2.flac', '/lib/2.flac', item_id=2)
        self.plugin._write_log()

        sessions = json.loads((self.tmp / 'import-log.json').read_text())
        self.assertEqual(len(sessions), 2)


class TestOnCliExit(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = Path(tempfile.mkdtemp())
        self.plugin = make_plugin(self.tmp)

    def test_writes_playlist_and_log_then_resets_state(self):
        self.plugin.on_import_begin(make_beets_session())
        items = [make_item('/lib/A/B/track.flac', 1)]
        task = make_album_task(items, ['/src/track.flac'])
        self.plugin.on_import_task_files(task, make_beets_session(is_move=True))

        self.plugin.on_cli_exit(MagicMock())

        self.assertEqual(len(list((self.tmp / 'playlists').glob('*.m3u'))), 1)
        self.assertTrue((self.tmp / 'import-log.json').exists())
        self.assertIsNone(self.plugin._session)
        self.assertEqual(self.plugin._paths, [])

    def test_does_nothing_when_no_session(self):
        self.plugin._session = None
        self.plugin.on_cli_exit(MagicMock())
        self.assertFalse((self.tmp / 'playlists').exists())
        self.assertFalse((self.tmp / 'import-log.json').exists())


if __name__ == '__main__':
    unittest.main()
