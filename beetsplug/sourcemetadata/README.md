# sourcemetadata

Adds a `source` field to the beets library and writes it as an audio file tag (FLAC and MP3 supported via mutagen).

## Usage

Pass `--set source=<value>` at import time:

```bash
beet import --set source=bandcamp <path>
```

Or set a default in your config so every import is tagged automatically.

If a file already has a `source` tag and no source is specified at import time, the existing tag is preserved.

## Config

```yaml
sourcemetadata:
  default_source: bandcamp        # used when --set source is not passed
  valid_sources:
    - bandcamp
    - soundcloud
    - tidal
    - qobuz
    - unknown
```

`default_source` defaults to `null` (no source). `valid_sources` controls what values are accepted — passing an unlisted value raises an error.
