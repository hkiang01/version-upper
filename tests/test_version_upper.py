import json
import logging
import os
import pathlib
import requests
import subprocess
from typing import List, Optional

import mock
import pytest
from click.testing import CliRunner

from version_upper import (
    DEFAULT_CONFIG_FILE,
    BumpPart,
    Config,
    SearchPattern,
    version_upper,
)

logger = logging.getLogger(__name__)


def __init_repo_with_version(path: str, content: str) -> str:
    """Creates a git repo in the current directory,
    and creates a commit with a sample file

    Parameters
    ----------
    file_name : str
        The path of the file to include in the initial commit
    contents : str
        The contents in the file included in the initial commit

    Returns
    -------
    str
        The commit hash of the initial commit
    """
    os.makedirs(pathlib.Path(path).parent)
    with open(path, "w") as f:
        f.write(content)
    subprocess.check_call(
        ["git", "config", "--global", "user.email", "you@example.com"]
    )
    subprocess.check_call(
        ["git", "config", "--global", "user.name", "Your Name"]
    )
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", path])
    subprocess.check_call(["git", "commit", "-m", "'initial commit'"])
    commit_hash = subprocess.check_output(
        ["git", "log", "-n1", "--format=format:%H"]
    ).decode()
    logger.debug(f"Initialized repo with {path} at commit {commit_hash}")
    return commit_hash


def bump_test_helper(
    config_file: str,
    cli_args: List[str],
    expected_exit_code: Optional[int] = 0,
    expected_output: Optional[str] = None,
    files_should_not_change: Optional[bool] = False,
    expected_new_semantic_version: Optional[str] = None,
    expected_new_version: Optional[str] = None,
    old_version: Optional[str] = None,
) -> str:
    """Helper to facilitate testing

    Runs cli command in isolated filesystem with the following setup:
        1. The file specified in "files" in the config_file
           is added to a new git repo
        2. config file is loaded with the file added

    After running the cli command, the following checks are made:
        1. Instances of old_version (if defined) are replaced
           with the expcted new version in the file specified in "files"
           in the config_file.
        2. Only current_version and current_semantic_version are changed
           in the config, and that they match the expected values
           (Note the cli implicitly performs validation using Pydnatic).

    Parameters
    ----------
    config_file : str
        The config file to use in the test
    cli_args : List[str]
        The args to pass to cli to bump version
    expected_exit_code : int, optional
        The expected status code of running cli with cli_args,
        by default 0
    expected_output : Optional[str]
        If defined, will be checked against the result
        of running cli with cli_args,
        by default None
    files_should_not_change : Optional[bool]
        If True, will check to make sure the file contents of config_file
        and file specified in "files" in the config_file
        have not changed after running cli with cli_args.
        If False, will check that the expected changes to config_file
        and the file specified in "files" in the config_file have been made,
        by default False
    expected_new_semantic_version : Optional[str]
        The new semantic version that should replace the old semantic version
        in the file specified in "files" in the config_file
        and in current_semantic_version in the config.
        Only checked if files_should_not_change is False
        by default None
    expected_new_version : Optional[str]
        The new version that should replace the old version
        in the file specified in "files" in the config_file
        and in current_version in the config. If not specified, then it will be
        the commit hash of the initial commit of the newly created git repo.
        Only checked if files_should_not_change is False
        By default None
    old_version : Optional[str]
        The old version that should not remain
        in the file specified in "files" in the config_file
        or in current_version in the config file after-the-fact,
        by default None

    Returns
    -------
    str
        The content of the file specified in "files" in the config_file
        after version_upper has run with cli_args
    """
    # load config
    with open(config_file) as f:
        config_file_dict = json.load(f)

    # validate config
    Config(**config_file_dict)

    files = config_file_dict["files"]
    assert len(files) == 1, (
        "Expecting only a single file. "
        "Feel free to update all the tests to accommodate more"
    )
    curr_file = files[0]
    if isinstance(curr_file, dict):
        curr_file = curr_file["path"]

    # load file
    with open(curr_file) as f:
        curr_file_contents = f.read()

    # load old config values (to test against config file after cli is run)
    # this list should not change
    old_files = config_file_dict["files"]

    runner = CliRunner()
    with runner.isolated_filesystem():
        # create git repo with file in fs
        commit_hash = __init_repo_with_version(curr_file, curr_file_contents)
        if expected_new_version is None:
            expected_new_version = commit_hash
        logger.debug(f"curr_file_contents before:\n{curr_file_contents}")
        # create config file in fs
        logger.debug(f"config_file_contents before:\n{config_file_dict}")
        with open(DEFAULT_CONFIG_FILE, "w") as f:
            json.dump(config_file_dict, f)

        # run command
        logger.debug(f"Running {cli_args}")
        result = runner.invoke(version_upper, cli_args, catch_exceptions=False)
        assert result.exit_code == expected_exit_code
        if expected_output:
            assert result.output == expected_output

        if files_should_not_change:
            with open(curr_file) as f:
                new_curr_file_contents = f.read()
                assert new_curr_file_contents == curr_file_contents
            with open(DEFAULT_CONFIG_FILE) as f:
                new_config_file_contents = json.load(f)
                assert new_config_file_contents == config_file_dict
        else:
            # check config file
            del config_file_dict
            with open(DEFAULT_CONFIG_FILE) as f:
                config_file_dict = json.load(f)
            logger.debug(f"config_file_contents after:\n{config_file_dict}")
            assert config_file_dict["files"] == old_files
            assert config_file_dict["current_version"] == expected_new_version
            assert (
                config_file_dict["current_semantic_version"]
                == expected_new_semantic_version
            )

            # check file
            with open(curr_file) as f:
                new_curr_file_contents = f.read()
            logger.debug(
                f"curr_file_contents after:\n{new_curr_file_contents}"
            )
            assert expected_new_version in new_curr_file_contents
            if old_version:
                assert old_version not in new_curr_file_contents

            # check current-version command output
            current_version_result = runner.invoke(
                version_upper, "current-version"
            )
            assert current_version_result.exit_code == 0
            assert current_version_result.output == expected_new_version + "\n"

            # check current-semantic-version command output
            current_version_result = runner.invoke(
                version_upper, "current-semantic-version"
            )
            assert current_version_result.exit_code == 0
            assert (
                current_version_result.output
                == expected_new_semantic_version + "\n"
            )
    return new_curr_file_contents


@pytest.mark.parametrize(
    "config_file_name,old_version,expected_new_semantic_version",
    [
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            "0.0.0",
        ),
        ("default.json", "0.0.0", "0.0.0",),
        ("existing_major.json", "1.0.0", "1.0.0",),
        ("existing_major_minor.json", "1.1.0", "1.1.0",),
        ("existing_minor.json", "0.1.0", "0.1.0",),
        ("existing_minor_patch.json", "0.1.1", "0.1.1",),
        ("existing_patch.json", "0.0.1", "0.0.1",),
        ("rc.json", "0.0.0rc1", "0.0.0",),
    ],
)
def test_bump_commit_hash(
    config_file_name, old_version, expected_new_semantic_version
):
    config_file = f"tests/sample_configs/{config_file_name}"

    bump_test_helper(
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version=old_version,
        expected_new_semantic_version=expected_new_semantic_version,
        expected_new_version=None,
    )


def test_bump_commit_hash_release_candidate():
    config_file = "tests/sample_configs/commit_hash.json"
    bump_test_helper(
        config_file=config_file,
        cli_args=["bump", "commit_hash", "--release-candidate"],
        old_version=None,
        expected_exit_code=2,
        expected_output=(
            "Usage: version-upper bump [OPTIONS] "
            "[major|minor|patch|rc|commit_hash]\n\n"
            "Error: Cannot use --release-candidate when bumping commit_hash\n"
        ),
        files_should_not_change=True,
    )


@pytest.mark.parametrize(
    (
        "config_file_name,old_version,cli_args,"
        "expected_new_semantic_version,expected_new_version"
    ),
    [
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "patch"],
            "0.0.1",
            "0.0.1",
        ),
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "patch", "--release-candidate"],
            "0.0.1",
            "0.0.1rc1",
        ),
        ("default.json", "0.0.0", ["bump", "patch"], "0.0.1", "0.0.1",),
        (
            "default.json",
            "0.0.0",
            ["bump", "patch", "--release-candidate"],
            "0.0.1",
            "0.0.1rc1",
        ),
        ("existing_major.json", "1.0.0", ["bump", "patch"], "1.0.1", "1.0.1",),
        (
            "existing_major.json",
            "1.0.0",
            ["bump", "patch", "--release-candidate"],
            "1.0.1",
            "1.0.1rc1",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "patch"],
            "1.1.1",
            "1.1.1",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "patch", "--release-candidate"],
            "1.1.1",
            "1.1.1rc1",
        ),
        ("existing_minor.json", "0.1.0", ["bump", "patch"], "0.1.1", "0.1.1",),
        (
            "existing_minor.json",
            "0.1.0",
            ["bump", "patch", "--release-candidate"],
            "0.1.1",
            "0.1.1rc1",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "patch"],
            "0.1.2",
            "0.1.2",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "patch", "--release-candidate"],
            "0.1.2",
            "0.1.2rc1",
        ),
        ("existing_patch.json", "0.0.1", ["bump", "patch"], "0.0.2", "0.0.2",),
        (
            "existing_patch.json",
            "0.0.1",
            ["bump", "patch", "--release-candidate"],
            "0.0.2",
            "0.0.2rc1",
        ),
        ("rc.json", "0.0.0rc1", ["bump", "patch"], "0.0.1", "0.0.1",),
        (
            "rc.json",
            "0.0.0rc1",
            ["bump", "patch", "--release-candidate"],
            "0.0.1",
            "0.0.1rc1",
        ),
    ],
)
def test_bump_patch(
    config_file_name,
    cli_args,
    old_version,
    expected_new_semantic_version,
    expected_new_version,
):
    config_file = f"tests/sample_configs/{config_file_name}"

    bump_test_helper(
        config_file=config_file,
        cli_args=cli_args,
        old_version=old_version,
        expected_new_semantic_version=expected_new_semantic_version,
        expected_new_version=expected_new_version,
    )


@pytest.mark.parametrize(
    (
        "config_file_name,old_version,cli_args,"
        "expected_new_semantic_version,expected_new_version"
    ),
    [
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "minor"],
            "0.1.0",
            "0.1.0",
        ),
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "minor", "--release-candidate"],
            "0.1.0",
            "0.1.0rc1",
        ),
        ("default.json", "0.0.0", ["bump", "minor"], "0.1.0", "0.1.0",),
        (
            "default.json",
            "0.0.0",
            ["bump", "minor", "--release-candidate"],
            "0.1.0",
            "0.1.0rc1",
        ),
        ("existing_major.json", "1.0.0", ["bump", "minor"], "1.1.0", "1.1.0",),
        (
            "existing_major.json",
            "1.0.0",
            ["bump", "minor", "--release-candidate"],
            "1.1.0",
            "1.1.0rc1",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "minor"],
            "1.2.0",
            "1.2.0",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "minor", "--release-candidate"],
            "1.2.0",
            "1.2.0rc1",
        ),
        ("existing_minor.json", "0.1.0", ["bump", "minor"], "0.2.0", "0.2.0",),
        (
            "existing_minor.json",
            "0.1.0",
            ["bump", "minor", "--release-candidate"],
            "0.2.0",
            "0.2.0rc1",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "minor"],
            "0.2.0",
            "0.2.0",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "minor", "--release-candidate"],
            "0.2.0",
            "0.2.0rc1",
        ),
        ("existing_patch.json", "0.0.1", ["bump", "minor"], "0.1.0", "0.1.0",),
        (
            "existing_patch.json",
            "0.0.1",
            ["bump", "minor", "--release-candidate"],
            "0.1.0",
            "0.1.0rc1",
        ),
        ("rc.json", "0.0.0rc1", ["bump", "minor"], "0.1.0", "0.1.0",),
        (
            "rc.json",
            "0.0.0rc1",
            ["bump", "minor", "--release-candidate"],
            "0.1.0",
            "0.1.0rc1",
        ),
    ],
)
def test_bump_minor(
    config_file_name,
    cli_args,
    old_version,
    expected_new_semantic_version,
    expected_new_version,
):
    config_file = f"tests/sample_configs/{config_file_name}"

    bump_test_helper(
        config_file=config_file,
        cli_args=cli_args,
        old_version=old_version,
        expected_new_semantic_version=expected_new_semantic_version,
        expected_new_version=expected_new_version,
    )


@pytest.mark.parametrize(
    (
        "config_file_name,old_version,cli_args,"
        "expected_new_semantic_version,expected_new_version"
    ),
    [
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "major"],
            "1.0.0",
            "1.0.0",
        ),
        (
            "commit_hash.json",
            "ae0788689030389e4be2654ad64ba983ba0b71c7",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
        ("default.json", "0.0.0", ["bump", "major"], "1.0.0", "1.0.0",),
        (
            "default.json",
            "0.0.0",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
        ("existing_major.json", "1.0.0", ["bump", "major"], "2.0.0", "2.0.0",),
        (
            "existing_major.json",
            "1.0.0",
            ["bump", "major", "--release-candidate"],
            "2.0.0",
            "2.0.0rc1",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "major"],
            "2.0.0",
            "2.0.0",
        ),
        (
            "existing_major_minor.json",
            "1.1.0",
            ["bump", "major", "--release-candidate"],
            "2.0.0",
            "2.0.0rc1",
        ),
        ("existing_minor.json", "0.1.0", ["bump", "major"], "1.0.0", "1.0.0",),
        (
            "existing_minor.json",
            "0.1.0",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "major"],
            "1.0.0",
            "1.0.0",
        ),
        (
            "existing_minor_patch.json",
            "0.1.1",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
        ("existing_patch.json", "0.0.1", ["bump", "major"], "1.0.0", "1.0.0",),
        (
            "existing_patch.json",
            "0.0.1",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
        ("rc.json", "0.0.0rc1", ["bump", "major"], "1.0.0", "1.0.0",),
        (
            "rc.json",
            "0.0.0rc1",
            ["bump", "major", "--release-candidate"],
            "1.0.0",
            "1.0.0rc1",
        ),
    ],
)
def test_bump_major(
    config_file_name,
    cli_args,
    old_version,
    expected_new_semantic_version,
    expected_new_version,
):
    config_file = f"tests/sample_configs/{config_file_name}"

    bump_test_helper(
        config_file=config_file,
        cli_args=cli_args,
        old_version=old_version,
        expected_new_semantic_version=expected_new_semantic_version,
        expected_new_version=expected_new_version,
    )


@pytest.mark.parametrize(
    (
        "config_file_name,old_version,cli_args,"
        "expected_new_semantic_version,expected_new_version"
    ),
    [
        ("default.json", None, ["bump", "rc"], "0.0.0", "0.0.0rc1"),
        ("existing_major.json", None, ["bump", "rc"], "1.0.0", "1.0.0rc1",),
        (
            "existing_major_minor.json",
            None,
            ["bump", "rc"],
            "1.1.0",
            "1.1.0rc1",
        ),
        ("existing_minor.json", None, ["bump", "rc"], "0.1.0", "0.1.0rc1",),
        (
            "existing_minor_patch.json",
            None,
            ["bump", "rc"],
            "0.1.1",
            "0.1.1rc1",
        ),
        ("existing_patch.json", None, ["bump", "rc"], "0.0.1", "0.0.1rc1",),
        ("rc.json", "0.0.0rc1", ["bump", "rc"], "0.0.0", "0.0.0rc2",),
    ],
)
def test_bump_rc(
    config_file_name,
    cli_args,
    old_version,
    expected_new_semantic_version,
    expected_new_version,
):
    config_file = f"tests/sample_configs/{config_file_name}"

    bump_test_helper(
        config_file=config_file,
        cli_args=cli_args,
        old_version=old_version,
        expected_new_semantic_version=expected_new_semantic_version,
        expected_new_version=expected_new_version,
    )


def test_bump_rc_release_candidate():
    config_file = "tests/sample_configs/default.json"
    bump_test_helper(
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_exit_code=2,
        expected_output=(
            "Usage: version-upper bump [OPTIONS] "
            "[major|minor|patch|rc|commit_hash]\n\n"
            "Error: Cannot use --release-candidate when bumping rc\n"
        ),
        files_should_not_change=True,
    )


def test_release_rc():
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        config_file=config_file,
        cli_args=["release"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0",
    )


def test_no_config_file_bump():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(version_upper, ["bump"])
        assert result.exit_code == 1
        assert (
            f"Error: Could not open file {DEFAULT_CONFIG_FILE}"
            in result.output
        )


def test_no_config_file_config_schema():
    runner = CliRunner()
    result = runner.invoke(version_upper, ["config-schema"])
    assert result.exit_code == 0
    assert json.loads(result.output) == Config.schema()


def test_no_config_file_current_semantic_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(version_upper, ["current-semantic-version"])
        assert result.exit_code == 1
        assert (
            f"Error: Could not open file {DEFAULT_CONFIG_FILE}"
            in result.output
        )


def test_no_config_file_current_version():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(version_upper, ["current-version"])
        assert result.exit_code == 1
        assert (
            f"Error: Could not open file {DEFAULT_CONFIG_FILE}"
            in result.output
        )


def test_no_config_file_release():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(version_upper, ["release"])
        assert result.exit_code == 1
        assert (
            f"Error: Could not open file {DEFAULT_CONFIG_FILE}"
            in result.output
        )


def test_no_config_file_sample_config():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(version_upper, ["sample-config"])
        assert result.exit_code == 0
        config = Config(**json.loads(result.output))
        assert isinstance(config, Config)


def test_illegal_release():
    config_file = "tests/sample_configs/default.json"
    bump_test_helper(
        config_file=config_file,
        cli_args=["release"],
        old_version=None,
        expected_exit_code=1,
        expected_output=(
            "Error: Unable to release if current version does not contain rc\n"
        ),
        files_should_not_change=True,
    )


@pytest.mark.parametrize("part", [bp.value for bp in BumpPart])
def test_config_current_version_not_present_bump(part):
    config_file = "tests/sample_configs/not_present.json"
    bump_test_helper(
        config_file=config_file,
        cli_args=["bump", part],
        old_version=None,
        expected_exit_code=1,
        expected_output=(
            "Error: Unable to find 0.0.0 in tests/sample_files/not_present.txt\n"
        ),
        files_should_not_change=True,
    )


def test_bump_invalid_part():
    config_file = "tests/sample_configs/default.json"
    bump_test_helper(
        config_file=config_file,
        cli_args=["bump", "asdf"],
        old_version=None,
        expected_exit_code=2,
        expected_output=(
            "Usage: version-upper bump [OPTIONS] "
            "[major|minor|patch|rc|commit_hash]\n"
            "Try 'version-upper bump --help' for help.\n\n"
            "Error: Invalid value for '[major|minor|patch|rc|commit_hash]': "
            "invalid choice: asdf. (choose from major, minor, patch, rc, "
            "commit_hash)\n"
        ),
        files_should_not_change=True,
    )


def test_main():
    # see https://medium.com/opsops/how-to-test-if-name-main-1928367290cb
    import version_upper  # noqa: F401

    with mock.patch.object(version_upper, "version_upper", return_value=42):
        with mock.patch.object(version_upper, "__name__", "__main__"):
            with mock.patch.object(version_upper.sys, "exit") as mock_exit:
                version_upper.init()
                assert mock_exit.call_args[0][0] == 42


@pytest.mark.skipif(
    json.loads(
        requests.get(
            "https://api.github.com/repos/samuelcolvin/pydantic/issues/1269"
        ).content
    )["state"]
    == "open",
    reason=(
        "Pydnatic has a bug where you can't get the schema of a BaseModel "
        "if it has within it a field of type Pattern. "
        "This will break the config-schema subcommand"
    ),
)
def test_pydantic_bug_1269():
    assert (
        SearchPattern.schema()["properties"]["search_pattern"]["type"]
        == "Pattern"
    )


def test_search():
    config_file = "tests/sample_configs/chart.json"

    bumped_file_contents = bump_test_helper(
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version=None,
        expected_new_semantic_version="1.16.1",
        expected_new_version="1.16.1",
    )

    with open("tests/sample_files/Chart_after.yaml") as f:
        expected_contents = f.read()
    assert bumped_file_contents == expected_contents
