import json
import logging
import pathlib
import subprocess
from typing import List, Optional

from click.testing import CliRunner

from version_upper import DEFAULT_CONFIG_FILE, cli

logger = logging.getLogger(__name__)


def __init_repo_with_version(file_name: str, content: str) -> str:
    """Creates a git repo in the current directory,
    and creates a commit with a sample file

    Parameters
    ----------
    file_name : str
        The file to include in the initial commit
    contents : str
        The contents in the file included in the initial commit

    Returns
    -------
    str
        The commit hash of the initial commit
    """
    with open(file_name, "w") as f:
        f.write(content)
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "add", file_name])
    subprocess.check_call(["git", "commit", "-m", "'initial commit'"])
    commit_hash = subprocess.check_output(
        ["git", "log", "-n1", "--format=format:%H"]
    ).decode()
    logger.debug(f"Initialized repo with {file_name} at commit {commit_hash}")
    return commit_hash


def bump_test_helper(
    config_file: str,
    version_file: str,
    cli_args: List[str],
    old_version: Optional[str],
    expected_new_semantic_version: str,
    expected_new_version: str = None,
):
    """Helper to facilitate testing

    Runs cli command in isolated filesystem with the following setup:
        1. version_file is added to a new git repo
        2. config file is loaded with the version_file added

    After running the cli command, the following checks are made:
        1. Instances of old_version (if defined) are replaced
           with the expcted new version in version_file.
        2. Only current_version and current_semantic_version are changed
           in the config, and that they match the expected values
           (Note the cli implicitly performs validation using Pydnatic).


    Parameters
    ----------
    config_file : str
        The config file to use in the test
    version_file : str
        The version file to use in the test (will be added to the config)
    cli_args : List[str]
        The args to pass to cli to bump version
    old_version : Optional[str]
        The old version that should not remain in version_file
        or in current_version in the config file after-the-fact
    expected_new_semantic_version : str
        The new semantic version that should replace the old semantic version
        in version_file and in current_semantic_version in the config.
    expected_new_version : str, optional
        The new version that should replace the old version in version_file
        and in current_version in the config. If not specified, then it will be
        the commit hash of the initial commit of the newly created git repo.
        By default None
    """
    # load version file
    with open(version_file) as f:
        version_file_contents = f.read()
    # load config
    with open(config_file) as f:
        config_file_contents = json.load(f)

    # load old config values (to test against config file after cli is run)
    old_files = config_file_contents["files"]
    version_file_name = pathlib.Path(version_file).name
    old_files.append(version_file_name)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # create git repo with version file in fs
        commit_hash = __init_repo_with_version(
            version_file_name, version_file_contents
        )
        if expected_new_version is None:
            expected_new_version = commit_hash
        logger.debug(f"version_file_contents before:\n{version_file_contents}")
        # create config file in fs
        config_file_contents["files"] = [version_file_name]
        logger.debug(f"config_file_contents before:\n{config_file_contents}")
        with open(DEFAULT_CONFIG_FILE, "w") as f:
            json.dump(config_file_contents, f)

        # run command
        logger.debug(f"Running {cli_args}")
        result = runner.invoke(cli, cli_args)
        assert result.exit_code == 0

        # check config file
        del config_file_contents
        with open(DEFAULT_CONFIG_FILE) as f:
            config_file_contents = json.load(f)
        logger.debug(f"config_file_contents after:\n{config_file_contents}")
        assert config_file_contents["files"] == old_files
        assert config_file_contents["current_version"] == expected_new_version
        assert (
            config_file_contents["current_semantic_version"]
            == expected_new_semantic_version
        )

        # check version file
        with open(version_file_name) as f:
            version_file_contents = f.read()
        logger.debug(f"version_file_contents after:\n{version_file_contents}")
        assert expected_new_version in version_file_contents
        if old_version:
            assert old_version not in version_file_contents


def test_bump_commit_hash_commit_hash():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="0.0.0",
        expected_new_version=None,
    )


def test_bump_commit_hash_default():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="0.0.0",
        expected_new_semantic_version="0.0.0",
        expected_new_version=None,
    )


def test_bump_commit_hash_existing_major():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="1.0.0",
        expected_new_semantic_version="1.0.0",
        expected_new_version=None,
    )


def test_bump_commit_hash_existing_major_minor():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="1.1.0",
        expected_new_semantic_version="1.1.0",
        expected_new_version=None,
    )


def test_bump_commit_hash_existing_minor():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="0.1.0",
        expected_new_semantic_version="0.1.0",
        expected_new_version=None,
    )


def test_bump_commit_hash_existing_minor_patch():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="0.1.1",
        expected_new_semantic_version="0.1.1",
        expected_new_version=None,
    )


def test_bump_commit_hash_existing_patch():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="0.0.1",
        expected_new_semantic_version="0.0.1",
        expected_new_version=None,
    )


def test_bump_commit_hash_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "commit_hash"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.0",
        expected_new_version=None,
    )


def test_bump_patch_commit_hash():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1",
    )


def test_bump_patch_commit_hash_release_candidate():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1rc1",
    )


def test_bump_patch_default():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="0.0.0",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1",
    )


def test_bump_patch_default_release_candidate():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="0.0.0",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1rc1",
    )


def test_bump_patch_existing_major():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="1.0.0",
        expected_new_semantic_version="1.0.1",
        expected_new_version="1.0.1",
    )


def test_bump_patch_existing_major_release_candidate():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="1.0.0",
        expected_new_semantic_version="1.0.1",
        expected_new_version="1.0.1rc1",
    )


def test_bump_patch_existing_major_minor():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="1.1.0",
        expected_new_semantic_version="1.1.1",
        expected_new_version="1.1.1",
    )


def test_bump_patch_existing_major_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="1.1.0",
        expected_new_semantic_version="1.1.1",
        expected_new_version="1.1.1rc1",
    )


def test_bump_patch_existing_minor():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="0.1.0",
        expected_new_semantic_version="0.1.1",
        expected_new_version="0.1.1",
    )


def test_bump_patch_existing_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="0.1.0",
        expected_new_semantic_version="0.1.1",
        expected_new_version="0.1.1rc1",
    )


def test_bump_patch_existing_minor_patch():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="0.1.1",
        expected_new_semantic_version="0.1.2",
        expected_new_version="0.1.2",
    )


def test_bump_patch_existing_minor_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="0.1.1",
        expected_new_semantic_version="0.1.2",
        expected_new_version="0.1.2rc1",
    )


def test_bump_patch_existing_patch():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="0.0.1",
        expected_new_semantic_version="0.0.2",
        expected_new_version="0.0.2",
    )


def test_bump_patch_existing_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="0.0.1",
        expected_new_semantic_version="0.0.2",
        expected_new_version="0.0.2rc1",
    )


def test_bump_patch_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1",
    )


def test_bump_patch_rc_release_candidate():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "patch", "--release-candidate"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1rc1",
    )


def test_bump_minor_commit_hash():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0",
    )


def test_bump_minor_commit_hash_release_candidate():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_minor_default():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="0.0.0",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0",
    )


def test_bump_minor_default_release_candidate():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="0.0.0",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_minor_existing_major():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="1.0.0",
        expected_new_semantic_version="1.1.0",
        expected_new_version="1.1.0",
    )


def test_bump_minor_existing_major_release_candidate():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="1.0.0",
        expected_new_semantic_version="1.1.0",
        expected_new_version="1.1.0rc1",
    )


def test_bump_minor_existing_major_minor():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="1.1.0",
        expected_new_semantic_version="1.2.0",
        expected_new_version="1.2.0",
    )


def test_bump_minor_existing_major_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="1.1.0",
        expected_new_semantic_version="1.2.0",
        expected_new_version="1.2.0rc1",
    )


def test_bump_minor_existing_minor():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="0.1.0",
        expected_new_semantic_version="0.2.0",
        expected_new_version="0.2.0",
    )


def test_bump_minor_existing_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="0.1.0",
        expected_new_semantic_version="0.2.0",
        expected_new_version="0.2.0rc1",
    )


def test_bump_minor_existing_minor_patch():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="0.1.1",
        expected_new_semantic_version="0.2.0",
        expected_new_version="0.2.0",
    )


def test_bump_minor_existing_minor_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="0.1.1",
        expected_new_semantic_version="0.2.0",
        expected_new_version="0.2.0rc1",
    )


def test_bump_minor_existing_patch():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="0.0.1",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0",
    )


def test_bump_minor_existing_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="0.0.1",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_minor_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0",
    )


def test_bump_minor_rc_release_candidate():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "minor", "--release-candidate"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_major_commit_hash():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_commit_hash_release_candidate():
    version_file = "tests/sample_version_files/commit_hash.json"
    config_file = "tests/sample_configs/commit_hash.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="ae0788689030389e4be2654ad64ba983ba0b71c7",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_major_default():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="0.0.0",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_default_release_candidate():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="0.0.0",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_major_existing_major():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="1.0.0",
        expected_new_semantic_version="2.0.0",
        expected_new_version="2.0.0",
    )


def test_bump_major_existing_major_release_candidate():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="1.0.0",
        expected_new_semantic_version="2.0.0",
        expected_new_version="2.0.0rc1",
    )


def test_bump_major_existing_major_minor():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="1.1.0",
        expected_new_semantic_version="2.0.0",
        expected_new_version="2.0.0",
    )


def test_bump_major_existing_major_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="1.1.0",
        expected_new_semantic_version="2.0.0",
        expected_new_version="2.0.0rc1",
    )


def test_bump_major_existing_minor():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="0.1.0",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_existing_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="0.1.0",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_major_existing_minor_patch():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="0.1.1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_existing_minor_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="0.1.1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_major_existing_patch():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="0.0.1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_existing_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="0.0.1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_major_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0",
    )


def test_bump_major_rc_release_candidate():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "major", "--release-candidate"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_rc_default():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0rc1",
    )


def test_bump_rc_default_release_candidate():
    version_file = "tests/sample_version_files/default.json"
    config_file = "tests/sample_configs/default.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0rc1",
    )


def test_bump_rc_existing_major():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_rc_existing_major_release_candidate():
    version_file = "tests/sample_version_files/existing_major.json"
    config_file = "tests/sample_configs/existing_major.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="1.0.0",
        expected_new_version="1.0.0rc1",
    )


def test_bump_rc_existing_major_minor():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="1.1.0",
        expected_new_version="1.1.0rc1",
    )


def test_bump_rc_existing_major_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_major_minor.json"
    config_file = "tests/sample_configs/existing_major_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="1.1.0",
        expected_new_version="1.1.0rc1",
    )


def test_bump_rc_existing_minor():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_rc_existing_minor_release_candidate():
    version_file = "tests/sample_version_files/existing_minor.json"
    config_file = "tests/sample_configs/existing_minor.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="0.1.0",
        expected_new_version="0.1.0rc1",
    )


def test_bump_rc_existing_minor_patch():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="0.1.1",
        expected_new_version="0.1.1rc1",
    )


def test_bump_rc_existing_minor_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_minor_patch.json"
    config_file = "tests/sample_configs/existing_minor_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="0.1.1",
        expected_new_version="0.1.1rc1",
    )


def test_bump_rc_existing_patch():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version=None,
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1rc1",
    )


def test_bump_rc_existing_patch_release_candidate():
    version_file = "tests/sample_version_files/existing_patch.json"
    config_file = "tests/sample_configs/existing_patch.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version=None,
        expected_new_semantic_version="0.0.1",
        expected_new_version="0.0.1rc1",
    )


def test_bump_rc_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0rc2",
    )


def test_bump_rc_rc_release_candidate():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["bump", "rc", "--release-candidate"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0rc2",
    )


def test_release_rc():
    version_file = "tests/sample_version_files/rc.json"
    config_file = "tests/sample_configs/rc.json"

    bump_test_helper(
        version_file=version_file,
        config_file=config_file,
        cli_args=["release"],
        old_version="0.0.0rc1",
        expected_new_semantic_version="0.0.0",
        expected_new_version="0.0.0",
    )
