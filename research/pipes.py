import numpy as np

from vectors import vec, normalize


def build_pipe(curve, curve_tang, thickness):

    def profile(t):
        return thickness * np.sin(t), thickness * np.cos(t)

    def profile_n(t):
        return np.sin(t), np.cos(t)


    def frame(u):
        Z = normalize(curve_tang(u))
        X = normalize(np.cross(Z, vec(0, 0, 1)))
        Y = normalize(np.cross(X, Z))
        return np.array([X, Y, Z])

    @np.vectorize(signature="(),()->(3)")
    def pipe(u, v):
        F = frame(u)
        a = curve(u)
        cx, cy = profile(v)
        c = np.array([cx, cy, 0])
        return a + c @ F

    @np.vectorize(signature="(),()->(3)")
    def normal(u, v):
        F = frame(u)
        cx, cy = profile_n(v)
        c = np.array([cx, cy, 0])
        return F.T @ c

    return pipe, normal