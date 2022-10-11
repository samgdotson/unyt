import numpy as np

from unyt.exceptions import UnitConversionError

_HANDLED_FUNCTIONS = {}


def implements(numpy_function):
    """Register an __array_function__ implementation for unyt_array objects."""
    # See NEP 18 https://numpy.org/neps/nep-0018-array-function-protocol.html
    def decorator(func):
        _HANDLED_FUNCTIONS[numpy_function] = func
        return func

    return decorator


@implements(np.array2string)
def array2string(a, *args, **kwargs):
    return (
        np.array2string._implementation(a, *args, **kwargs)
        + f", units={str(a.units)!r}"
    )


def _get_conversion_factor(out, units) -> float:
    # helper function to "product"-like functions with an 'out' argument
    try:
        return (1 * out.units).to(units).d
    except (AttributeError, UnitConversionError) as exc:
        raise TypeError(
            "output array is not acceptable "
            f"(units '{out.units}' cannot be converted to '{units}')"
        ) from exc


@implements(np.dot)
def dot(a, b, out=None):
    prod_units = a.units * b.units
    if out is None:
        return np.dot._implementation(a.ndview, b.ndview) * prod_units

    conv_factor = _get_conversion_factor(out, prod_units)

    np.dot._implementation(a.ndview, b.ndview, out=out.ndview)
    if not out.units == prod_units:
        out[:] *= conv_factor
    return out


@implements(np.vdot)
def vdot(a, b):
    return np.vdot._implementation(a.ndview, b.ndview) * (a.units * b.units)


@implements(np.inner)
def inner(a, b):
    return np.inner._implementation(a.ndview, b.ndview) * (a.units * b.units)


@implements(np.outer)
def outer(a, b, out=None):
    prod_units = a.units * b.units
    if out is None:
        return np.outer._implementation(a.ndview, b.ndview) * prod_units

    conv_factor = _get_conversion_factor(out, prod_units)

    np.outer._implementation(a.ndview, b.ndview, out=out.ndview)
    if not out.units == prod_units:
        out[:] *= conv_factor
    return out


@implements(np.kron)
def kron(a, b):
    return np.kron._implementation(a.ndview, b.ndview) * (a.units * b.units)


@implements(np.matmul)
def matmul(a, b, out=None, **kwargs):
    prod_units = a.units * b.units
    if out is None:
        return np.matmul._implementation(a.ndview, b.ndview) * prod_units

    conv_factor = _get_conversion_factor(out, prod_units)
    np.matmul._implementation(a.ndview, b.ndview, out=out.ndview)
    if not out.units == prod_units:
        out[:] *= conv_factor
    return out


@implements(np.linalg.inv)
def linalg_inv(a, *args, **kwargs):
    return np.linalg.inv._implementation(a.ndview, *args, **kwargs) / a.units


@implements(np.linalg.tensorinv)
def linalg_tensorinv(a, *args, **kwargs):
    return np.linalg.tensorinv._implementation(a, *args, **kwargs) / a.units


@implements(np.linalg.pinv)
def linalg_pinv(a, *args, **kwargs):
    return np.linalg.pinv._implementation(a, *args, **kwargs).ndview / a.units


def _sanitize_range(_range, units):
    # helper function to histogram* functions
    ndim = len(units)
    if _range is None:
        return _range
    new_range = np.empty((ndim, 2))
    for i in range(ndim):
        ilim = _range[2 * i : 2 * (i + 1)]
        imin, imax = ilim
        if not (hasattr(imin, "units") and hasattr(imax, "units")):
            raise TypeError(
                f"Elements of range must both have a 'units' attribute. Got {_range}"
            )
        new_range[i] = imin.to(units[i]).value, imax.to(units[i]).value
    return new_range.squeeze()


@implements(np.histogram)
def histogram(
    a,
    bins=10,
    range=None,
    normed=None,
    weights=None,
    density=None,
):
    range = _sanitize_range(range, units=[a.units])
    counts, bins = np.histogram._implementation(
        a.ndview,
        bins=bins,
        range=range,
        normed=normed,
        weights=weights,
        density=density,
    )
    return counts, bins * a.units


@implements(np.histogram2d)
def histogram2d(
    x,
    y,
    bins=10,
    range=None,
    normed=None,
    weights=None,
    density=None,
):
    range = _sanitize_range(range, units=[x.units, y.units])
    counts, xbins, ybins = np.histogram2d._implementation(
        x.ndview,
        y.ndview,
        bins=bins,
        range=range,
        normed=normed,
        weights=weights,
        density=density,
    )
    return counts, xbins * x.units, ybins * y.units


@implements(np.histogramdd)
def histogramdd(
    sample,
    bins=10,
    range=None,
    normed=None,
    weights=None,
    density=None,
):
    units = [_.units for _ in sample]
    range = _sanitize_range(range, units=units)
    counts, bins = np.histogramdd._implementation(
        [_.ndview for _ in sample],
        bins=bins,
        range=range,
        normed=normed,
        weights=weights,
        density=density,
    )
    return counts, tuple(_bin * u for _bin, u in zip(bins, units))
