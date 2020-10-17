import numpy as np
from scipy.spatial import SphericalVoronoi


def voronoi(points):
    v = SphericalVoronoi(points)
    vertices = v.vertices
    points = v.points
    regions = v.regions
    areas = v.calculate_areas()

    return list(map(
        lambda ix: (points[ix], vertices[regions[ix]], areas[ix]),
        np.arange(0, len(points))
    ))


def voronoi_s1(points, normalize=True):
    if normalize:
        norm = np.linalg.norm(points, axis=1)
        mask = ~np.isclose(norm, 0)
        points[mask] /= norm[mask]

    return voronoi(points)


def voronoi_sn(points, precision=1E-6):
    norm = np.linalg.norm(points, axis=1)
    points = points[norm > 0.]
    norm = norm[norm > 0.]

    sort_idx = np.argsort(norm)
    shells, s, n = np.unique(
        (norm[sort_idx] / precision).astype(np.int64),
        return_counts=True, return_index=True
    )

    shells = shells.astype(np.float64) * precision

    voronoi = []
    norm = norm[sort_idx]
    points = points[sort_idx]

    for shell, st, ct in zip(shells, s, n):
        pts = points[st:st + ct] / norm[st:st + ct][:, None]
        if ct > 2:
            voronoi.append((
                shell, voronoi_s1(pts, False)
            ))
        else:
            voronoi.append((shell, []))

    return voronoi
