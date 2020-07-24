# version-upper

[![Build Status](https://travis-ci.com/hkiang01/version-upper.svg?branch=master)](https://travis-ci.com/hkiang01/version-upper)
[![Coverage](https://coveralls.io/repos/github/hkiang01/version-upper/badge.svg?branch=master&service=github )](https://coveralls.io/github/hkiang01/version-upper?branch=master)

Primarily a reaction to [bumpversion](https://github.com/peritus/bumpversion) not supporting git hashes -- [issue](https://github.com/peritus/bumpversion/issues/125)

## Overview

```
Usage: version-upper [OPTIONS] COMMAND [ARGS]...

  A tool to update version strings in files using semantic versioning and
  commit hashes.

  Examples:

  # bump commit sha version
  version-upper bump commit_sha

  # bump patch version
  version-upper bump patch

  # bump patch version as release candidate
  version-upper bump patch --release-candidate

  # bump minor version
  version-upper bump minor

  # bump major version
  version-upper bump major

  The config file adheres to the Config Pydantic schema, and is named
  version_conifg.json by default.

  Here is a sample config:
  {
      "current_version": "0.0.0",
      "current_semantic_version": "0.0.0",
      "files": []
  }

Options:
  --config TEXT  [default: version_upper.json]
  --help         Show this message and exit.

Commands:
  bump                      Bumps version strings, updates config.
  config-schema             Prints the config schema in JSON
  current-semantic-version  Prints the current semantic version
  current-version           Prints the current version
  release                   Removes rc from the version strings
  sample-config             Prints a sample config
```

## Configuration

Create a file called `version_upper.json` (can be overridden using `--config`) like below:

```json
{
  "current_version": "0.0.0",
  "current_semantic_version": "0.0.0",
  "files": ["main.py", "app/version.json"]
}
```

Be sure to add files to `"files"` otherwise nothing will be updated :)
