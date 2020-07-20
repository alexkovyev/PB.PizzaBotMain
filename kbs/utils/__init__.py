"""
The :mod:`kbs.utils` module includes various utilities.
"""
from collections.abc import Sequence
from itertools import compress
import struct
import platform
import numbers

import numpy as np
from scipy.sparse import issparse

from ..exceptions import DataConversionWarning
from .fixes import np_version

__all__ = [
    "DataConversionWarning",
    "array_indexing",
    "list_indexing",
    "determine_key_type",
    "tosequence",
    "to_object_array",
    "message_with_time",
    "is_scalar_nan"
]

IS_PYPY = platform.python_implementation() == 'PyPy'
_IS_32BIT = 8 * struct.calcsize("P") == 32


class Bunch(dict):
    """Container object exposing keys as attributes
    Bunch objects are sometimes used as an output for functions and methods.
    They extend dictionaries by enabling values to be accessed by key,
    `bunch["value_key"]`, or by an attribute, `bunch.value_key`.
    Examples
    --------
    >>> b = Bunch(a=1, b=2)
    >>> b['b']
    2
    >>> b.b
    2
    >>> b.a = 3
    >>> b['a']
    3
    >>> b.c = 6
    >>> b['c']
    6
    """

    def __init__(self, **kwargs):
        super().__init__(kwargs)

    def __setattr__(self, key, value):
        self[key] = value

    def __dir__(self):
        return self.keys()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)

    def __setstate__(self, state):
        pass


def array_indexing(array, key, key_dtype, axis):
    """Index an array or scipy.sparse consistently across NumPy version."""
    if np_version < (1, 12) or issparse(array):
        # FIXME: Remove the check for NumPy when using >= 1.12
        # check if we have an boolean array-likes to make the proper indexing
        if key_dtype == 'bool':
            key = np.asarray(key)
    if isinstance(key, tuple):
        key = list(key)
    return array[key] if axis == 0 else array[:, key]


def list_indexing(X, key, key_dtype):
    """Index a Python list."""
    if np.isscalar(key) or isinstance(key, slice):
        # key is a slice or a scalar
        return X[key]
    if key_dtype == 'bool':
        # key is a boolean array-like
        return list(compress(X, key))
    # key is a integer array-like of key
    return [X[idx] for idx in key]


def determine_key_type(key, accept_slice=True):
    """Determine the data type of key.
    Parameters
    ----------
    key : scalar, slice or array-like
        The key from which we want to infer the data type.
    accept_slice : bool, default=True
        Whether or not to raise an error if the key is a slice.
    Returns
    -------
    dtype : {'int', 'str', 'bool', None}
        Returns the data type of key.
    """
    err_msg = ("No valid specification of the columns. Only a scalar, list or "
               "slice of all integers or all strings, or boolean mask is "
               "allowed")

    dtype_to_str = {int: 'int', str: 'str', bool: 'bool', np.bool_: 'bool'}
    array_dtype_to_str = {'i': 'int', 'u': 'int', 'b': 'bool', 'O': 'str',
                          'U': 'str', 'S': 'str'}

    if key is None:
        return None
    if isinstance(key, tuple(dtype_to_str.keys())):
        try:
            return dtype_to_str[type(key)]
        except KeyError:
            raise ValueError(err_msg)
    if isinstance(key, slice):
        if not accept_slice:
            raise TypeError(
                'Only array-like or scalar are supported. '
                'A Python slice was given.'
            )
        if key.start is None and key.stop is None:
            return None
        key_start_type = _determine_key_type(key.start)
        key_stop_type = _determine_key_type(key.stop)
        if key_start_type is not None and key_stop_type is not None:
            if key_start_type != key_stop_type:
                raise ValueError(err_msg)
        if key_start_type is not None:
            return key_start_type
        return key_stop_type
    if isinstance(key, (list, tuple)):
        unique_key = set(key)
        key_type = {_determine_key_type(elt) for elt in unique_key}
        if not key_type:
            return None
        if len(key_type) != 1:
            raise ValueError(err_msg)
        return key_type.pop()
    if hasattr(key, 'dtype'):
        try:
            return array_dtype_to_str[key.dtype.kind]
        except KeyError:
            raise ValueError(err_msg)
    raise ValueError(err_msg)


def tosequence(x):
    """Cast iterable x to a Sequence, avoiding a copy if possible.
    Parameters
    ----------
    x : iterable
    """
    if isinstance(x, np.ndarray):
        return np.asarray(x)
    elif isinstance(x, Sequence):
        return x
    else:
        return list(x)


def to_object_array(sequence):
    """Convert sequence to a 1-D NumPy array of object dtype.
    numpy.array constructor has a similar use but it's output
    is ambiguous. It can be 1-D NumPy array of object dtype if
    the input is a ragged array, but if the input is a list of
    equal length arrays, then the output is a 2D numpy.array.
    _to_object_array solves this ambiguity by guarantying that
    the output is a 1-D NumPy array of objects for any input.
    Parameters
    ----------
    sequence : array-like of shape (n_elements,)
        The sequence to be converted.
    Returns
    -------
    out : ndarray of shape (n_elements,), dtype=object
        The converted sequence into a 1-D NumPy array of object dtype.
    Examples
    --------
    >>> import numpy as np
    >>> from kbs.utils import _to_object_array
    >>> _to_object_array([np.array([0]), np.array([1])])
    array([array([0]), array([1])], dtype=object)
    >>> _to_object_array([np.array([0]), np.array([1, 2])])
    array([array([0]), array([1, 2])], dtype=object)
    >>> np.array([np.array([0]), np.array([1])])
    array([[0],
       [1]])
    >>> np.array([np.array([0]), np.array([1, 2])])
    array([array([0]), array([1, 2])], dtype=object)
    """
    out = np.empty(len(sequence), dtype=object)
    out[:] = sequence
    return out


def message_with_time(source, message, time):
    """Create one line message for logging purposes
    Parameters
    ----------
    source : str
        String indicating the source or the reference of the message
    message : str
        Short message
    time : int
        Time in seconds
    """
    start_message = "[%s] " % source

    if time > 60:
        time_str = "%4.1fmin" % (time / 60)
    else:
        time_str = " %5.1fs" % time
    end_message = " %s, total=%s" % (message, time_str)
    dots_len = (70 - len(start_message) - len(end_message))
    return "%s%s%s" % (start_message, dots_len * '.', end_message)


def is_scalar_nan(x):
    """Tests if x is NaN
    This function is meant to overcome the issue that np.isnan does not allow
    non-numerical types as input, and that np.nan is not np.float('nan').
    Parameters
    ----------
    x : any type
    Returns
    -------
    boolean
    Examples
    --------
    >>> is_scalar_nan(np.nan)
    True
    >>> is_scalar_nan(float("nan"))
    True
    >>> is_scalar_nan(None)
    False
    >>> is_scalar_nan("")
    False
    >>> is_scalar_nan([np.nan])
    False
    """
    # convert from numpy.bool_ to python bool to ensure that testing
    # is_scalar_nan(x) is True does not fail.
    return bool(isinstance(x, numbers.Real) and np.isnan(x))
