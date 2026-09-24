# [`gcloud topic uninstall`](topic-uninstall.md)

## NAME

    [`gcloud topic uninstall`](topic-uninstall.md) - supplementary help for uninstalling Google Cloud
        CLI

## DESCRIPTION

Uninstalling Google Cloud CLI

    Note: For installations completed using an OS package (such as apt-get,
    yum, etc.), uninstall Google Cloud CLI via the OS package manager.

    Note: For Windows installations, execute the uninstaller.exe found under
    your Google Cloud CLI directory.

    To completely remove Google Cloud CLI, follow these instructions:

      o Locate your installation directory by running:

        $ gcloud info --format="value(installation.sdk_root)"

      o Locate your user config directory (typically ~/.config/gcloud on
        MacOS and Linux) by running:

        $ gcloud info --format="value(config.paths.global_config_dir)"

      o Delete both these directories.

      o Additionally, remove lines sourcing completion.bash.inc and
        paths.bash.inc in your .bashrc or equivalent shell init file, if you
        added them during installation.

      o Review the contents of the .boto file in your home directory and
        remove the sections '[GoogleCompute]' and '[GSUtil]'. In addition,
        review the sections '[OAuth2]' and '[Credentials]' for settings that
        are no longer needed.

      o Some systems may have Cache directories such as ~/Library/Caches/ on
        Mac OS X. Find and delete these directories for your system:

        $ find ~/Library/Caches/ -type d -name "google-cloud-sdk" | xargs \
        rm -r