import numpy as np

def vec(x, y, z=None):
    if z is None:
        return np.array([x, y], dtype=np.float32)
    else:
        return np.array([x, y, z], dtype=np.float32)

def length(v):
    return np.sqrt(np.dot(v, v))

def normalize(v):
    return v / length(v)