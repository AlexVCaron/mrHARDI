import numpy as np


def extrapolate_reference(
    dwi, bvals, bvecs, n_target, target_bvals, target_bvecs,
    mask=None, subspace_fit=True
):
    shape = dwi.shape
    target_shape = dwi.shape
    target_shape[3] = n_target

    log_image = dwi.reshape((np.prod(shape[:3]), shape[3]))
    log_image = np.log(log_image.astype(np.float64))
    log_image[np.isinf(log_image)] = np.nan

    x = np.concatenate(
        (get_btensors(bvals, bvecs).T * 1E-9, np.ones(len(bvals))[None, :]),
        axis=0
    )

    if np.linalg.matrix_rank(x @ x.T, 1E-10) < 7:
        if subspace_fit:
            e = np.zeros((4, 7))
            e[(0, 1, 2, 3), (0, 1, 2, 6)] = 1
        else:
            e = np.eye(7)

    dt = np.linalg.lstsq((e @ x).T, log_image.T)[0].T @ e

    if mask is not None:
        dt2 = np.copy(dt)
        nan_mask = np.isnan(dt[:, 0])
        for idx in np.where(nan_mask):
            d_tmp = np.zeros((1, dt.shape[1])
            c_tmp = 0

            for i in [-1, 0, 1]:
                for j in [-1, 0, 1]:
                    for k in [-1, 0, 1]:
                        if np.any(np.isnan(dt[idx + [i, j, k], :])):
                            continue

                        d_tmp += dt[idx + [i, j, k], :]
                        c_tmp += 1

            dt2[idx, :] = d_tmp / c_tmp

        dt = dt2

    dt = np.real(dt)
    md = np.mean(dt[:,:3], axis=1)
    d_tissue = 0.75; # Bennett2003 average
    d_csf = 2.1; # lower than true value due to PVE in estimation
    f_csf = (md - d_tissue) / (d_csf - d_tissue)
    f_csf[f_csf < 0] = 0;
    f_csf[f_csf > 0.99] = 0.99

    dt2 = np.copy(dt)
    dt2[:, :3] = (
        dt2[:, :3] - d_csf * np.tile(f_csf, (1, 3)) / 
        (1. - np.tile(f_csf, (1, 3)))
    )
    md2 = np.mean(dt2[:,:3], axis=2)
    dt2[md2 > d_tissue, :3] = d_tissue
    dt2[md2 > d_tissue, 3:) = 0
    md2 = np.mean(dt2[:,:3], axis=2)

    dt3 = np.copy(dt2)
    d_min = 0.3
    ind_low = md2 < d_min;
    dt3[ind_low, :3] = dt[ind_low, :3] + (d_min - np.tile(md2[ind_low], (1, 3)))

    d_max = 1.2
    alpha = 0.8 # Bennet 2003, stretched exponential

    b_target = np.tile(target_bvals.T, (dt3.shape[0], 1))
    bt_target = get_btensors(target_bvals, target_bvecs)
    d = dt3[:, :6] @ bt_target.T / b_target
    d[d < d_min] = d_min
    d[d > d_max] = d_max
    d *= 1e-9
    d_csf = 3e-9
    s0 = np.tile(np.exp(dt3[:, 6]), (1, n_target))

    ref = (s0 * (
        np.tile(1. - f_csf, (1, n_target)) * np.exp(-(d * b_target) ** alpha) +
        np.tile(f_csf, (1, n_target)) * np.exp(-b_target * d_csf)
    )).reshape(shape)
    ref[np.isnan(ref)] = 0

    return ref
