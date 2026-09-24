# gcloud config configurations activate

## NAME

    gcloud config configurations activate - activates an existing named
        configuration

## SYNOPSIS

```bash
    gcloud config configurations activate CONFIGURATION_NAME
        [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    Activates an existing named configuration.

    See [`gcloud topic configurations`](../topic/topic-configurations.md) for an overview of named configurations.

## EXAMPLES

    To activate an existing configuration named my-config, run:

        $ gcloud config configurations activate my-config

    To list all properties in the activated configuration, run:

        $ gcloud config list --all

## POSITIONAL ARGUMENTS

     CONFIGURATION_NAME
        Name of the configuration to activate

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.