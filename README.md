# version_upper

[![Build Status](https://travis-ci.com/hkiang01/version_upper.svg?branch=master)](https://travis-ci.com/hkiang01/version_upper)
[![Coverage Status](https://coveralls.io/repos/github/hkiang01/version_upper/badge.svg?branch=master)](https://coveralls.io/github/hkiang01/version_upper?branch=master)

Primarily a reaction to [bumpversion](https://github.com/peritus/bumpversion) not supporting git hahes -- [issue](https://github.com/peritus/bumpversion/issues/125)

```
python version_upper.py --help

Usage: version_upper.py [OPTIONS] COMMAND [ARGS]...

  A tool to update version strings in files using semantic versioning and
  commit hashes.

  Examples:

  # bump commit sha version
  python version_upper.py bump commit_sha

  # bump patch version
  python version_upper.py bump patch

  # bump patch version as release candidate
  python version_upper.py bump patch --release-candidate

  # bump minor version
  python version_upper.py bump minor

  # bump major version
  python version_upper.py bump major

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
  add-files                 Adds files/directories to config.
  bump                      Bumps version strings, updates config.
  config-schema             Prints the config schema in JSON
  current-semantic-version  Prints the current semantic version
  current-version           Prints the current version
  files                     Prints files in which bump will replace version...
  release                   Removes rc from the version strings
  sample-config             Prints a sample config
```
