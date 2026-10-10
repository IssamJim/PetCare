"""Registration tests use a separate MySQL database, never petcaredb's records."""
from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        **DATABASES["default"],  # noqa: F405
        "TEST": {"NAME": "test_petcaredb_registration"},
    },
}
