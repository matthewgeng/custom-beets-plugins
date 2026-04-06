# symlinkonmove

After a move import, creates a symlink at each file's original path pointing to its new location in the beets library. Also moves image artifacts (cover art, etc.) to the library directory and symlinks them back.

Only activates when `move = yes` is in effect. Has no effect on copy or link imports.

## Purpose

Preserves the original folder structure as symlinks after beets reorganises files on import, so other tools pointing at the original paths don't immediately break.

## Config

No configuration options. Enable by adding `symlinkonmove` to your plugins list.

```yaml
plugins:
  - symlinkonmove
```
