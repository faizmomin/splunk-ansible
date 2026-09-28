#!/usr/bin/env python
"""Contract tests for App Manager provisioning."""

from __future__ import absolute_import

import os

import yaml


FILE_DIR = os.path.dirname(os.path.realpath(__file__))
REPO_DIR = os.path.join(FILE_DIR, "..", "..")


def load_yaml(relative_path):
    with open(os.path.join(REPO_DIR, relative_path)) as stream:
        return yaml.safe_load(stream)


def read_file(relative_path):
    with open(os.path.join(REPO_DIR, relative_path)) as stream:
        return stream.read()


def named_task(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def test_app_manager_role_matrix_is_explicit():
    defaults = load_yaml("roles/splunk_app_manager/defaults/main.yml")

    assert defaults["splunk_app_manager_enabled"] is False
    assert defaults["splunk_app_manager_supported_roles"] == [
        "splunk_search_head",
        "splunk_indexer",
        "splunk_ingestor",
    ]
    assert defaults["splunk_app_manager_sync_script"] == "configs_sync.py"


def test_common_role_installs_app_manager_at_the_prestart_boundary():
    tasks = load_yaml("roles/splunk_common/tasks/main.yml")
    install = named_task(tasks, "Install and configure App Manager before full splunkd startup")

    assert install["include_role"]["name"] == "splunk_app_manager"
    assert install["when"] == [
        "splunk_app_manager_enabled | default(false) | bool",
        'splunk.role in ["splunk_search_head", "splunk_indexer", "splunk_ingestor"]',
    ]

    config_index = next(
        i for i, task in enumerate(tasks)
        if task.get("include_tasks") == "set_config_file.yml"
    )
    install_index = tasks.index(install)
    start_index = next(
        i for i, task in enumerate(tasks)
        if task.get("include_tasks") == "start_splunk.yml"
    )
    assert config_index < install_index < start_index


def test_role_validates_source_settings_and_supported_roles():
    text = read_file("roles/splunk_app_manager/tasks/main.yml")

    assert "splunk.role in splunk_app_manager_supported_roles" in text
    assert 'match("^s3://[^/]+/.+")' in text
    assert "splunk_app_manager_remote_bundle" in text
    assert "splunk_app_manager_aws_region" in text


def test_install_is_marker_based_staged_and_rollback_safe():
    text = read_file("roles/splunk_app_manager/tasks/install.yml")

    assert "splunk_app_manager_source_marker" in text
    assert "splunk_app_manager_archive_uri" in text
    assert "splunk_app_manager_install_required" in text
    assert "splunk_app_manager_staging_root" in text
    assert "splunk_app_manager_backup" in text
    assert "Restore App Manager after an interrupted replacement" in text
    assert "Reject symbolic links" in text
    assert "rescue:" in text
    assert "Restore the preserved App Manager payload" in text

    tasks = load_yaml("roles/splunk_app_manager/tasks/install.yml")
    install = named_task(tasks, "Install the selected App Manager artifact")
    download = named_task(install["block"], "Download the selected App Manager artifact")
    assert download["command"]["argv"][1:3] == ["s3", "cp"]
    assert download["environment"]["AWS_REGION"] == "{{ splunk_app_manager_aws_region }}"


def test_role_owns_only_app_manager_local_configuration():
    text = read_file("roles/splunk_app_manager/tasks/configure.yml")

    assert "{{ splunk_app_manager_target }}/local/server.conf" in text
    assert "{{ splunk_app_manager_target }}/local/inputs.conf" in text
    assert "splunk_app_manager_sync_stanza" in text
    assert "Keep the Noah client disabled on ingestors" in text
    assert "splunk.role == \"splunk_ingestor\"" in text
    assert "option: disabled" in text
    assert 'value: "0"' in text
    assert "option: run_only_one" in text
    assert "splunk.role == \"splunk_search_head\"" in text
    assert "{{ splunk.home }}/etc/aws_ec2_region_cache" in text
