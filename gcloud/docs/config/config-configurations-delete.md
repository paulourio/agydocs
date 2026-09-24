# gcloud config configurations delete

## NAME

    gcloud config configurations delete - deletes a named configuration

## SYNOPSIS

```bash
    gcloud config configurations delete CONFIGURATION_NAMES
        [CONFIGURATION_NAMES ...] [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    Deletes a named configuration. You cannot delete a configuration that is
    active, even when overridden with the --configuration flag. To delete the
    current active configuration, first gcloud config configurations activate
    another one.

    See [`gcloud topic configurations`](../topic/topic-configurations.md) for an overview of named configurations.

## EXAMPLES

    To delete an existing configuration named my-config, run:

        $ gcloud config configurations delete my-config

    To delete more than one configuration, run:

        $ gcloud config configurations delete my-config1 my-config2

    To list existing configurations, run:

        $ gcloud config configurations list

## POSITIONAL ARGUMENTS

     CONFIGURATION_NAMES [CONFIGURATION_NAMES ...]
        Name of the configuration to delete. Cannot be currently active
        configuration.

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.