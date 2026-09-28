# App Manager provisioning role

This opt-in role installs and configures App Manager before the first full
splunkd start. It is intentionally separate from `splunk.apps_location`, which
does not install apps locally on clustered search-head and indexer members.

Supported roles are `splunk_search_head`, `splunk_indexer`, and
`splunk_ingestor`. Unsupported roles fail validation when the feature is
enabled.

Supply the following values through the generated `default.yml` consumed by
splunk-ansible:

```yaml
splunk_app_manager_enabled: true
splunk_app_manager_archive_uri: s3://kraken-app-bucket/ansible/100-app-manager_VERSION.tgz
splunk_app_manager_remote_bundle: s3://kraken-runtime-bucket/app-manager-poc
splunk_app_manager_cloud_provider: aws
splunk_app_manager_aws_region: us-west-2
```

The archive URI is recorded in
`100-app-manager/.splunk-ansible-source`. Re-running the role with the same URI
does not reinstall the app, but always reconciles its local configuration.
Changing the URI stages and validates the new payload before replacing the
existing directory. If activation fails, the role restores the old payload.

The role writes:

- `100-app-manager/local/server.conf`, containing the stack-specific Noah
  bundle location and cloud provider. This bundle-sync-only POC sets
  `disabled=true` for the Splunk Noah client on every supported role. App
  Manager still reads `remoteBundle` directly. SPL-313974 will define the
  complete Noah client configuration and enablement for Linus;
- `100-app-manager/local/inputs.conf`, enabling `configs_sync.py`;
- `etc/aws_ec2_region_cache`, used by the Splunk Python AWS helpers.

The App Manager package keeps the generic input disabled by default so existing
deployment mechanisms remain unchanged. This role enables it only because the
app itself is installed only on supported nodes.
