# skipaliases

Skips import tasks where every file in the task is a symlink. This prevents beets from re-importing albums that were already imported and are now represented only by symlinks (e.g. created by `symlinkonmove`).

## Purpose

When using `symlinkonmove` with `--incremental`, beets may try to re-import the symlinks left behind in the original folder. This plugin drops those tasks before any DB writes or file operations occur.

## Config

No configuration options. Enable by adding `skipaliases` to your plugins list.

```yaml
plugins:
  - skipaliases
```
