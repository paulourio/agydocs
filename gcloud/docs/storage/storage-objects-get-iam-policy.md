# gcloud storage objects get-iam-policy

## NAME

    gcloud storage objects get-iam-policy - get the access policy for an object

## SYNOPSIS

```bash
    gcloud storage objects get-iam-policy URL [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    gcloud storage objects get-iam-policy behaves similarly to gcloud storage
    objects get-object-acl, but uses the IAM policy binding syntax in the
    output.

## EXAMPLES

    To get the access policy for OBJECT in BUCKET:

        $ gcloud storage objects get-iam-policy gs://BUCKET/OBJECT

    To output the access policy for OBJECT in BUCKET to a file:

        $ gcloud storage objects get-iam-policy gs://BUCKET/OBJECT > \
            policy.txt

## POSITIONAL ARGUMENTS

     URL
        Request IAM policy for this object.

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.

## NOTES

### This command is an internal implementation detail and may change or

    disappear without notice.
