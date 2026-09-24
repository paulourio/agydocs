# gcloud config configurations rename

## NAME

    gcloud config configurations rename - renames a named configuration

## SYNOPSIS

```bash
    gcloud config configurations rename CONFIGURATION_NAME --new-name=NEW_NAME
        [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    Renames a named configuration.

    See [`gcloud topic configurations`](../topic/topic-configurations.md) for an overview of named configurations.

## EXAMPLES

    To rename an existing configuration named my-config, run:

        $ gcloud config configurations rename my-config --new-name=new-config

## POSITIONAL ARGUMENTS

     CONFIGURATION_NAME
        Name of the configuration to rename

## REQUIRED FLAGS

     --new-name=NEW_NAME
        Specifies the new name of the configuration.

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.