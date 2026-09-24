# gcloud compute firewall-rules describe

## NAME

    gcloud compute firewall-rules describe - describe a Compute Engine firewall
        rule

## SYNOPSIS

```bash
    gcloud compute firewall-rules describe NAME [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    gcloud compute firewall-rules describe displays all data associated with a
    Compute Engine firewall rule in a project.

## EXAMPLES

    To describe a firewall rule, run:

        $ gcloud compute firewall-rules describe my-firewall-rule

## POSITIONAL ARGUMENTS

     NAME
        Name of the firewall rule to describe.

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.