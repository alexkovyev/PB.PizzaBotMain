"""
The :mod:`kbs.exceptions` module includes all custom warnings and error
classes used across kbs.
"""

__all__ = [
    'DataConversionWarning',
    'BridgeError',

]


class DataConversionWarning(UserWarning):
    """Warning used to notify implicit data conversions happening in the code.
    This warning occurs when some input data needs to be converted or
    interpreted in a way that may not match the user's expectations.
    For example, this warning may occur when the user
        - passes an integer array to a function which expects float input and
          will convert the input
        - requests a non-copying operation, but a copy is required to meet the
          implementation's data-type expectations;
        - passes an input whose shape can be interpreted ambiguously.
       Moved from kbs.utils.validation.
    """


class BridgeError(Exception):
    """
    Class for errors that can occure while db_bridge object
    executes query or connects to the db.
    """

    def __init__(self, proc_name, params, error):
        self.proc_name = proc_name
        self.params = params
        self.error = error

    def __str__(self):
        return "Procedure: {proc}\nParams: {params}\nError: {error}".format(
            proc=self.proc_name,
            params=self.params,
            error=self.error.__str__()
        )

class NoFreeOvenError(Exception):
    pass


# оставить 1?
class OvenReservationError(Exception):
    pass


class OvenReserveFailed(Exception):
    pass

class BrokenOvenHandlerError(Exception):
    pass
