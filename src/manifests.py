import logging
from pathlib import Path

from lightkube import Client, codecs
from lightkube.core.exceptions import ApiError

log = logging.getLogger(__file__)


class Manifests:
    def __init__(self, charm):
        self.namespace = charm.model.name
        self.application = charm.model.app.name
        self.client = Client(namespace=self.namespace, field_manager="lightkube")

    def apply_manifests(self):
        with open(Path("upstream", "manifests", "rendered.yaml")) as f:
            text = f.read()
            text = text.replace("juju-application-placeholder", self.application)
            text = text.replace("juju-namespace-placeholder", self.namespace)
        for obj in codecs.load_all_yaml(text):
            self.delete_resource(
                type(obj),
                obj.metadata.name,
                ignore_not_found=True,
            )
            self.client.create(obj)

    def delete_manifest(self, namespace=None, ignore_not_found=False, ignore_unauthorized=False):
        with open(Path("upstream", "manifests", "rendered.yaml")) as f:
            text = f.read()
            text = text.replace("juju-application-placeholder", self.application)
            text = text.replace("juju-namespace-placeholder", self.namespace)
        for obj in codecs.load_all_yaml(text):
            self.delete_resource(
                type(obj),
                obj.metadata.name,
                namespace=namespace,
                ignore_not_found=ignore_not_found,
                ignore_unauthorized=ignore_unauthorized,
            )

    def delete_resource(
        self,
        resource_type,
        name,
        namespace=None,
        ignore_not_found=False,
        ignore_unauthorized=False,
    ):
        """Delete a resource."""
        try:
            self.client.delete(resource_type, name, namespace=namespace)
        except ApiError as err:
            log.exception("ApiError encountered while attempting to delete resource.")
            if err.status.message is not None:
                if "not found" in err.status.message and ignore_not_found:
                    log.error(f"Ignoring not found error:\n{err.status.message}")
                elif "(Unauthorized)" in err.status.message and ignore_unauthorized:
                    # Ignore error from https://bugs.launchpad.net/juju/+bug/1941655
                    log.error(f"Ignoring unauthorized error:\n{err.status.message}")
                else:
                    log.error(err.status.message)
                    raise
            else:
                raise
