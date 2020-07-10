"""Compatibility fixes for older version of python and numpy
If you add content to this file, please give the version of the package
at which the fixe is no longer needed.
"""
# Authors: Vadim Zhdanov <zhdanov.vdm@icloud.com>
#
# License: MIT License

import numpy as np
import scipy


def _parse_version(version_string):
    version = []
    for x in version_string.split('.'):
        try:
            version.append(int(x))
        except ValueError:
            # x may be of the form dev-1ea1592
            version.append(x)
    return tuple(version)


np_version = _parse_version(np.__version__)
sp_version = _parse_version(scipy.__version__)

if sp_version >= (1, 4):
    from scipy.sparse.linalg import lobpcg
else:
    from ..externals._lobpcg import lobpcg  # type: ignore  # noqa


def _object_dtype_isnan(X):
    return X != X