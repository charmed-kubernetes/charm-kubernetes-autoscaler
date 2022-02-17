from config.scale import JujuScale
from config.controller import JujuController
from config.ca_cert import JujuCaCert
from config.model import JujuModel


def validate_juju_config(opt, potential):
    if opt == "scale":
        return JujuScale(potential)
    elif opt == "api_endpoints":
        return JujuController(potential)
    elif opt == "ca_cert":
        return JujuCaCert(potential)
    elif opt == "model_uuid":
        return JujuModel(potential)
    return potential


__all__ = ["JujuScale", "JujuController", "JujuCaCert", "JujuModel", "validate_juju_config"]
