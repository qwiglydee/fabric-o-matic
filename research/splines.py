import numpy as np

M1 = np.array([[1, 0], [-1, 1]], dtype=np.float32)

B2 = np.array([[1, 1, 0], [-2, 2, 0], [1, -2, 1]], dtype=np.float32) / 2
B3 = np.array([[1, 4, 1, 0], [-3, 0, 3, 0], [3, -6, 3, 0], [-1, 3, -3, 1]], dtype=np.float32) / 6

Bezier2 = np.array([[1, 0, 0], [-2, 2, 0], [1, -2, 1]], dtype=np.float32)
Bezier3 = np.array([[1, 0, 0, 0], [-3, 3, 0, 0], [3, -6, 3, 0], [-1, 3, -3, 1]], dtype=np.float32)


Cardinal = lambda s: np.array([[0, 1, 0, 0], [-s, 0, s, 0], [2 * s, s - 3, 3 - 2 * s, -s], [-s, 2 - s, s - 2, s]], dtype=np.float32)

CatmullRom = np.array([[0, 2, 0, 0], [-1, 0, 1, 0], [2, -5, 4, -1], [-1, 3, -3, 1]], dtype=np.float32) / 2


def powers(tt, d):
    "[1, t, t^2, ..., t^d]"
    return np.array([tt**d for d in range(d + 1)])


def powers_dt(tt, d):
    "[1, t, t^2, ..., t^d]"
    return np.array([0] + [d * tt ** (d - 1) for d in range(1, d + 1)])


def premul(M, cpoints):
    """premultiply M with all points
    assuming support of i-th segment is P_{i} ... P_{i+d}
    """
    d = M.shape[0] - 1
    n = cpoints.shape[0]
    return [M @ cpoints[i : i + d + 1] for i in range(0, n - d)]

def wrap(t, imin=0, imax=0):
    "split t into segment idx and local u: t -> i, u"
    i, u = np.divmod(t, 1.0)
    i = int(i)
    if i > imax:
        return imax, t - imax
    if i < imin:
        return imin, t - imin
    return i, u

def build_curve(M, cpoints):
    "build all points of curve with characteristic matrix and control points, for all t's"
    d = M.shape[0] - 1
    cc = premul(M, cpoints)  # list
    nsegs = len(cc)

    @np.vectorize(signature="()->(3)")
    def curve(t):
        i, u = wrap(t, 0, nsegs - 1)
        return powers(u, d) @ cc[i]

    @np.vectorize(signature="()->(3)")
    def curve_dt(t):
        i, u = wrap(t, 0, nsegs - 1)
        return powers_dt(u, d) @ cc[i]

    return curve, curve_dt
