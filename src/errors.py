from ops.model import BlockedStatus


class JujuEnvironmentError(Exception):
    pass


class JujuConfigError(BlockedStatus):
    pass
