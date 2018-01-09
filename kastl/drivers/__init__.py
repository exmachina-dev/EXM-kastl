from .abstract_driver import AbstractDriver, AbstractDriverError, AbstractTimeoutError
from .frontend import DriverFrontend
from importlib import import_module


def get_driver(driver):
    pkg = import_module("kastl.drivers.%s" % driver.lower())
    return getattr(pkg, "%sDriver" % driver.title())
