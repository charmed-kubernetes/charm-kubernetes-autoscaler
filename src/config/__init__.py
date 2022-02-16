from config.scale import JujuScale
from config.controller import JujuController
from config.ca_cert import JujuCaCert
from config.model import JujuModel

__all__ = ["JujuScale", "JujuController", "JujuCaCert", "JujuModel"]


def validate_juju_config(opt, potential):
    if opt == "scale":
        return JujuScale.parse(potential)
    elif opt == "api_endpoints":
        return JujuController.parse(potential)
    elif opt == "ca_cert":
        return JujuCaCert.parse(potential)
    elif opt == "model_uuid":
        return JujuModel.parse(potential)
    return potential
