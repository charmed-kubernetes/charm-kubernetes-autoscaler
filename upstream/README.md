# Upstream Manifests

This directory contains local copies of the upstream manifests from the release
commit supported by this charm to be used by the charm for deployment. These
files should not be modified locally.

## Updating

To update these, simply run the update script, passing in the release branch,
tag, or commit to update to:

```bash
./upstream/update.sh [version]
```

This will overwrite the existing rendered manifests for the charm