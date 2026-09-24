# gcloud storage objects set-iam-policy

## NAME

    gcloud storage objects set-iam-policy - set access policy for an object

## SYNOPSIS

```bash
    gcloud storage objects set-iam-policy URLS [URLS ...] POLICY_FILE
        [--all-versions] [--continue-on-error, -c] [--etag=ETAG, -e ETAG]
        [--recursive, -R, -r] [GCLOUD_WIDE_FLAG ...]

```

## DESCRIPTION

    gcloud storage objects set-iam-policy behaves similarly to gcloud storage
    objects set-object-acl, but uses the IAM policy binding syntax.

## EXAMPLES

### To set the access policy for OBJECT on BUCKET to the policy defined in

    POLICY-FILE run:

        $ gcloud storage objects set-iam-policy gs://BUCKET/OBJECT \
            POLICY-FILE

### To set the IAM policy in POLICY-FILE on all objects in all buckets

    beginning with "b":

        $ gcloud storage objects set-iam-policy -r gs://b* POLICY-FILE

## POSITIONAL ARGUMENTS

     URLS [URLS ...]
        The URLs for objects whose access policy is being replaced.

     POLICY_FILE
        Path to a local JSON or YAML formatted file containing a valid policy.

        The output of the get-iam-policy command is a valid file, as is any
        JSON or YAML file conforming to the structure of a Policy
        (https://cloud.google.com/iam/reference/rest/v1/Policy).

## FLAGS

     --all-versions
        Update the IAM policies of all versions of an object in a versioned
        bucket.

     --continue-on-error, -c
        If any operations are unsuccessful, the command will exit with a
        non-zero exit status after completing the remaining operations. This
        flag takes effect only in sequential execution mode (i.e. processor and
        thread count are set to 1). Parallelism is default.

     --etag=ETAG, -e ETAG
        Custom etag to set on IAM policy. API will reject etags that do not
        match this value, making it useful as a precondition during concurrent
        operations.

     --recursive, -R, -r
        Recursively set the IAM policies of the contents of any directories
        that match the source path expression.

## GCLOUD WIDE FLAGS

    These flags are available to all commands: --access-token-file, --account,
    --billing-project, --configuration, --flags-file, --flatten, --format,
    --help, --impersonate-service-account, --log-http, --project, --quiet,
    --trace-token, --user-output-enabled, --verbosity.

    Run $ gcloud help for details.

## NOTES

### This command is an internal implementation detail and may change or

    disappear without notice.
