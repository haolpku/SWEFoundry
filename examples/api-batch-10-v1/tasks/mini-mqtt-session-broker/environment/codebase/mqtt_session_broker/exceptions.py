class MqttBrokerError(Exception):
    """Base class for deterministic broker benchmark errors."""


class MqttParseError(MqttBrokerError):
    """Raised when event JSON cannot be decoded or has the wrong shape."""


class MqttValidationError(MqttBrokerError):
    """Raised when MQTT benchmark inputs violate the public contract."""
