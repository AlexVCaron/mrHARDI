from copy import deepcopy
from enum import Enum

import numpy as np


class B0PostProcess(Enum):
    whole = "whole"
    batch = "batch"
    none = None


class B0Reference(Enum):
    first = "first"
    last = "last"
    linear = "linear"


def pick_b0(b0_mask, b0_strides):
    first_b0_idx = b0_mask.argmax()
    for i in range(first_b0_idx, len(b0_mask)):
        if b0_mask[i]:
            if i + b0_strides >= len(b0_mask) and b0_mask[-1]:
                b0_mask[i + 1:len(b0_mask) - 1] = False
                continue
            b0_mask[i + 1:i + b0_strides] = False

    return b0_mask


def mean_b0_clusters(dwi_img, b0_mask, output_shape):
    b0_clusters = np.ma.notmasked_contiguous(b0_mask, axis=0)
    output_vol = np.zeros(output_shape + (len(b0_clusters),))
    for i, cluster in enumerate(b0_clusters):
        output_vol[..., i] = np.mean(dwi_img.dataobj[..., cluster], axis=-1)

    return output_vol


def extract_b0(
    dwi_img, bvals, b0_strides=None, mean=B0PostProcess.none, ceil=0.9,
    b0_comp=np.less_equal, metadata=None, dtype=None
):
    b0_mask = b0_comp(bvals, ceil)
    mask = np.ma.masked_array(b0_mask)
    mask[~b0_mask] = np.ma.masked

    dtype = dtype if dtype else dwi_img.get_data_dtype()

    if b0_strides:
        b0_mask[:dwi_img.shape[-1]] = pick_b0(
            b0_mask[:dwi_img.shape[-1]], b0_strides
        )

    if mean is B0PostProcess.batch:
        mask = np.ma.masked_array(b0_mask)
        mask[~b0_mask] = np.ma.masked
        b0_vols = mean_b0_clusters(dwi_img, mask, dwi_img.shape[:-1])

        if metadata:
            clusters = np.ma.notmasked_contiguous(mask, axis=0)

            acquisition = metadata.acquisition_slices_to_list()
            metadata.update_acquisition_from_list([
                acquisition[cluster.start] for cluster in clusters
            ])

            metadata.n = b0_vols.shape[-1]

            directions = []
            for i, cl in enumerate(clusters):
                for d in metadata.directions:
                    if d["range"][1] > cl.start >= d["range"][0]:
                        directions.append({
                            "dir": d["dir"],
                            "range": (i, i + 1)
                        })

            dd = [directions[0]]
            for d in directions[1:]:
                if dd[-1]["dir"] == d["dir"]:
                    dd[-1]["range"] = (
                        dd[-1]["range"][0],
                        d["range"][1]
                    )
                else:
                    dd.append(d)

            metadata.directions = dd
    else:
        b0_clusters = np.ma.notmasked_contiguous(mask, axis=0)
        idx, b0_vols = 0, np.zeros(dwi_img.shape[:-1] + (np.sum(mask),))
        for cluster in b0_clusters:
            len_cluster = cluster.stop - cluster.start
            b0_vols[..., idx:idx + len_cluster] = dwi_img.dataobj[..., cluster]
            idx += len_cluster

        if metadata:
            acquisition = (np.array(
                metadata.acquisition_slices_to_list()
            )[b0_mask[:dwi_img.shape[-1]]]).tolist()
            metadata.update_acquisition_from_list(acquisition)

            directions = []
            start = 0
            for cl in b0_clusters:
                curr_cl = deepcopy(cl)
                for i, d in enumerate(metadata.directions):
                    if d["range"][1] > curr_cl.start >= d["range"][0]:
                        n = min(curr_cl.stop, d["range"][1]) - curr_cl.start
                        lg = curr_cl.stop > d["range"][1]
                        directions.append({
                            "dir": d["dir"],
                            "range": (start, start + n)
                        })
                        start += n
                        if lg:
                            curr_cl = slice(d["range"][1], curr_cl.stop)
                        else:
                            break

            dd = [directions[0]]
            for d in directions[1:]:
                if dd[-1]["dir"] == d["dir"]:
                    dd[-1]["range"] = (
                        dd[-1]["range"][0],
                        d["range"][1]
                    )
                else:
                    dd.append(d)

            metadata.directions = dd

            metadata.n = b0_vols.shape[-1]

        if mean is B0PostProcess.whole:
            b0_vols = np.mean(b0_vols, axis=-1)[..., None]

            if metadata:
                metadata.n = 1
                metadata.acquisition_types = [metadata.acquisition_types[0]]
                metadata.acquisition_slices = [[0, None]]
                metadata.directions = [{
                    "dir": metadata.directions[0]["dir"],
                    "range": (0, 1)
                }]

    return b0_vols.astype(dtype)


def squash_b0(
    dwi_img, bvals, bvecs, mean=B0PostProcess.batch,
    ceil=0.9, b0_comp=np.less_equal, metadata=None, dtype=None
):
    b0_mask = b0_comp(bvals, ceil)
    mask = np.ma.masked_array(b0_mask)
    mask[~b0_mask] = np.ma.masked

    b0_clusters = list(np.ma.notmasked_contiguous(mask, axis=0))
    dwi_clusters = list(np.ma.clump_masked(mask))

    dtype = dtype if dtype else dwi_img.get_data_dtype()

    if mean is B0PostProcess.whole:
        if np.sum(b0_mask) == 1:
            return (dwi_img.get_fdata().astype(dtype), bvals, bvecs)
        else:
            meta_b0 = metadata.copy() if metadata else None
            output = np.zeros(dwi_img.shape[:3] + (1 + np.sum(~b0_mask),))
            output[..., 0] = extract_b0(
                dwi_img, bvals, mean=mean, ceil=ceil,
                b0_comp=b0_comp, metadata=meta_b0, dtype=dtype
            )

            if metadata:
                for cl in b0_clusters:
                    curr_cl = deepcopy(cl)
                    for i, d in enumerate(metadata.directions):
                        if d["range"][1] > curr_cl.start >= d["range"][0]:
                            n = min(curr_cl.stop, d["range"][1]) - curr_cl.start
                            lg = curr_cl.stop > d["range"][1]
                            d["range"] = (d["range"][0], d["range"][1] - n)
                            if lg:
                                curr_cl = slice(d["range"][1], curr_cl.stop)
                            else:
                                break

                acquisition = metadata.acquisition_slices_to_list()
                metadata.update_acquisition_from_list(
                    (np.array(acquisition)[~b0_mask]).tolist()
                )

                metadata.n = int(np.sum(~b0_mask))

                meta_b0.extend(metadata)
                metadata.becomes(meta_b0)

            idx = 1
            for cluster in dwi_clusters:
                len_cluster = cluster.stop - cluster.start
                output[..., idx:idx + len_cluster] = dwi_img.dataobj[..., cluster]
                idx += len_cluster

            ret_tuple = (
                output.astype(dtype), np.hstack(([0], bvals[~b0_mask]))[None, :]
            )

            if bvecs is not None:
                ret_tuple += (np.hstack(([[0], [0], [0]], bvecs[:, ~b0_mask])),)
            else:
                ret_tuple += (None,)

            return ret_tuple
    elif all(cl.stop - cl.start == 1 for cl in b0_clusters):
        return (dwi_img.get_fdata().astype(dtype), bvals, bvecs)

    if metadata:
        for cl in b0_clusters:
            curr_cl = deepcopy(cl)
            lg = False
            for i, d in enumerate(metadata.directions):
                if d["range"][1] > curr_cl.start >= d["range"][0]:
                    n = min(curr_cl.stop, d["range"][1]) - curr_cl.start
                    if not lg:
                        n -= 1
                    lg = curr_cl.stop > d["range"][1]
                    d["range"] = (d["range"][0], d["range"][1] - n)
                    if lg:
                        curr_cl = slice(d["range"][1], curr_cl.stop)
                    else:
                        break

        mb_mask = b0_mask[:dwi_img.shape[-1]].copy()
        for cluster in b0_clusters:
            mb_mask[cluster.start] = False

        acquisition = metadata.acquisition_slices_to_list()
        metadata.update_acquisition_from_list(
            (np.array(acquisition)[~mb_mask]).tolist()
        )

        metadata.n = int(np.sum(~b0_mask) + len(b0_clusters))

    output_shape = dwi_img.shape[:-1] + (
        dwi_img.shape[-1] + len(b0_clusters) - np.sum(b0_mask),
    )

    data = np.zeros(output_shape)
    out_bvals = []
    out_bvecs = []

    if mean is B0PostProcess.none:
        b0_extractor = lambda cluster: cluster[..., 0]
    else:
        b0_extractor = lambda cluster: np.mean(cluster, axis=-1)

    if len(dwi_clusters) > len(b0_clusters):
        data[..., dwi_clusters[0]] = dwi_img.dataobj[..., dwi_clusters[0]]
        out_bvals += bvals[dwi_clusters[0]].tolist()
        if bvecs is not None:
            out_bvecs += bvecs[:, dwi_clusters[0]].T.tolist()
        dwi_clusters = dwi_clusters[1:]

    shape_reduce = 0
    for i in range(len(dwi_clusters)):
        data[..., b0_clusters[i].start - shape_reduce] = b0_extractor(
            dwi_img.dataobj[..., b0_clusters[i]]
        )
        out_bvals.append(0)
        if bvecs is not None:
            out_bvecs.append([0, 0, 0])
        shape_reduce += b0_clusters[i].stop - b0_clusters[i].start - 1
        data_slice = slice(
            dwi_clusters[i].start - shape_reduce,
            dwi_clusters[i].stop - shape_reduce
        )
        data[..., data_slice] = dwi_img.dataobj[..., dwi_clusters[i]]
        out_bvals += bvals[dwi_clusters[i]].tolist()
        if bvecs is not None:
            out_bvecs += bvecs[:, dwi_clusters[i]].T.tolist()

    if len(b0_clusters) > len(dwi_clusters):
        data[..., -1] = b0_extractor(dwi_img.dataobj[..., b0_clusters[-1]])
        out_bvals.append(0)
        if bvecs is not None:
            out_bvecs.append([0, 0, 0])

    return (
        data.astype(dtype),
        np.array(out_bvals)[None, ...],
        np.array(out_bvecs).T if bvecs is not None else None
    )


def normalize_to_b0(
    data, bvals, mean=B0PostProcess.batch,
    ref_strategy=B0Reference.linear, ref_mean=None,
    ceil=0.9, b0_comp=np.less_equal
):
    reference_last = ref_strategy == B0Reference.last

    if reference_last:
        data = data[..., ::-1]
        bvals = bvals[::-1]
        ref_strategy = B0Reference.first

    b0_mask = b0_comp(bvals, ceil)
    mask = np.ma.masked_array(b0_mask)
    mask[~b0_mask] = np.ma.masked

    b0_clusters = list(np.ma.notmasked_contiguous(mask, axis=0))
    dwi_clusters = list(np.ma.clump_masked(mask))

    if ref_mean is None:
        ref_mean = np.mean(data[..., b0_clusters[0]])

    if not b0_comp(bvals[0], ceil):
        dwi_clusters = dwi_clusters[1:]
    if not b0_comp(bvals[-1], ceil):
        if mean == B0PostProcess.batch:
            mean_val = np.mean(data[..., b0_clusters[-1]])
        else:
            mean_val = np.mean(data[..., b0_clusters[-1].start])

        if not np.isclose(mean_val, 0):
            data[..., dwi_clusters[-1]] *= ref_mean / mean_val

        dwi_clusters = dwi_clusters[:-1]

    for i in range(len(dwi_clusters)):
        len_cl = dwi_clusters[i].stop - dwi_clusters[i].start

        if mean == B0PostProcess.batch:
            mean_val = np.mean(data[..., b0_clusters[i]])
        else:
            mean_val = np.mean(data[..., b0_clusters[i].stop - 1])

        if ref_strategy == B0Reference.linear:
            weight = np.arange(len_cl).astype(float) / (len_cl - 1.)
            if mean == B0PostProcess.batch:
                mean_val_p1 = np.mean(data[..., b0_clusters[i + 1]])
            else:
                mean_val_p1 = np.mean(data[..., b0_clusters[i + 1].start])
            modif = weight * mean_val_p1 + (1. - weight) * mean_val
        else:
            modif = mean_val

        for mod, cl in zip(modif, dwi_clusters[i]):
            if not np.isclose(mod, 0.):
                data[..., cl] *= ref_mean / mod

    for i in range(len(b0_clusters)):
        mean_cluster = np.mean(data[..., b0_clusters[i]])
        if not np.isclose(mean_cluster, 0.):
            data[..., b0_clusters[i]] *= ref_mean / mean_cluster

    if reference_last:
        data = data[..., ::-1]

    return data, ref_mean
