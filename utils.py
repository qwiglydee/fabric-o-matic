from collections.abc import Iterable, Iterator
from typing import Any

import math
import numpy as np
from numpy.typing import NDArray, ArrayLike

npvec = np.ndarray[tuple[int]]


def arr(args: ArrayLike) -> NDArray[np.float32]:
    return np.array(args, dtype=np.float32)


def garr(gen: Iterator[Any]) -> NDArray[np.float32]:
    return np.array(tuple(gen), dtype=np.float32)


def arrgs(*args: ArrayLike) -> NDArray[np.float32]:
    return np.array(args, dtype=np.float32)


def f32(arr: NDArray[Any]) -> NDArray[np.float32]:
    return arr.astype(np.float32)


def npdots(aa: NDArray, bb: NDArray) -> NDArray:
    return (aa * bb).sum(1)


def disquance(p1: npvec, p2: npvec) -> float:
    pd = p1 - p2
    return np.dot(pd, pd)


def negligible(v: Iterable[Any], eps=5e-7) -> bool:
    return all(c < eps for c in v)


def unflat(v: npvec) -> npvec:
    return arrgs(v[0], v[1], 0.0)


def unflat_np(vv: NDArray) -> NDArray:
    return np.vstack((vv.T, np.zeros(vv.shape[0]))).T


def normalize(v: npvec) -> npvec:
    l: float = 1 / math.sqrt(np.dot(v, v))
    return v * l
