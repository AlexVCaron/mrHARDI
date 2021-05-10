from copy import deepcopy
from enum import Enum

import numpy as np


class B0PostProcess(Enum):
    whole = "whole"
    batch = "batch"
    none = None


def pick_b0(b0_mask, b0_strides):
    first_b0_idx = b0_mask.argmax()
    for i in range(first_b0_idx, len(b0_mask)):
        if b0_mask[i]:
            if i + b0_strides >= len(b0_mask) and b0_mask[-1]:
                b0_mask[i + 1:len(b0_mask) - 1] = False
                continue
            b0_mask[i + 1:i + b0_strides] = False

    return b0_mask


def mean_b0_clusters(dwi_img, mask, output_shape):
    b0_clusters = np.ma.notmasked_contiguous(mask, axis=0)
    output_vol = np.zeros(output_shape + (0,))
    for cluster in b0_clusters:
        output_vol = np.concatenate((
            output_vol,
            np.mean(dwi_img.dataobj[..., cluster].reshape(
                output_shape + (-1,)), axis=-1
            )[..., None]
        ), axis=-1)

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
        print("Extracting b0 volumes at each {} volumes".format(b0_strides))
        b0_mask[:dwi_img.shape[-1]] = pick_b0(
            b0_mask[:dwi_img.shape[-1]], b0_strides
        )

    if mean is B0PostProcess.batch:
        print("Applying mean to b0 in batch")
        mask = np.ma.masked_array(b0_mask)
        mask[~b0_mask] = np.ma.masked
        b0_vol = mean_b0_clusters(dwi_img, mask, dwi_img.shape[:-1])
        print("Found {} mean b0 volumes in dataset".format(b0_vol.shape[-1]))

        if metadata:
            clusters = np.ma.notmasked_contiguous(mask, axis=0)

            acquisition = metadata.acquisition_slices_to_list()
            metadata.update_acquisition_from_list([
                acquisition[cluster.start] for cluster in clusters
            ])

            metadata.n = b0_vol.shape[-1]

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
        b0_vol = np.zeros(dwi_img.shape[:-1] + (0,))
        for cluster in b0_clusters:
            b0_vol = np.concatenate((
                b0_vol,
                dwi_img.dataobj[..., cluster]
            ), axis=-1)

        if metadata:
            print(metadata.acquisition_slices_to_list())
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
                            curr_cl.start = d["range"][1]
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

            metadata.n = b0_vol.shape[-1]

        print("Found {} b0 volumes in dataset".format(b0_vol.shape[-1]))

        if mean is B0PostProcess.whole:
            print("Applying mean to whole b0 volume")
            b0_vol = np.mean(b0_vol, axis=-1)[..., None]

            if metadata:
                metadata.n = 1
                metadata.acquisition_types = [metadata.acquisition_types[0]]
                metadata.acquisition_slices = [[0, None]]
                metadata.directions = [{
                    "dir": metadata.directions[0]["dir"],
                    "range": (0, 1)
                }]

    return b0_vol.astype(dtype)


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
        meta_b0 = metadata.copy() if metadata else None
        b0 = extract_b0(
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
                            curr_cl.start = d["range"][1]
                        else:
                            break

            acquisition = metadata.acquisition_slices_to_list()
            metadata.update_acquisition_from_list(
                (np.array(acquisition)[~b0_mask]).tolist()
            )

            metadata.n = int(np.sum(~b0_mask))

            meta_b0.extend(metadata)
            metadata.becomes(meta_b0)

        for cluster in dwi_clusters:
            b0 = np.concatenate((
                b0,
                dwi_img.dataobj[..., cluster]
            ), axis=-1)

        ret_tuple = (
            b0.astype(dtype), np.hstack(([0], bvals[~b0_mask]))[None, :]
        )

        if bvecs is not None:
            ret_tuple += (np.hstack(([[0], [0], [0]], bvecs[:, ~b0_mask])),)
        else:
            ret_tuple += (None,)

        return ret_tuple

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
                        curr_cl.start = d["range"][1]
                    else:
                        break

        mb_mask = b0_mask[:dwi_img.shape[-1]].copy()
        for cluster in b0_clusters:
            mb_mask[cluster.start] = False
        idxs = np.where(~mb_mask)[0].tolist()

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
    ceil=0.9, ref_mean=None, b0_comp=np.less_equal
):
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
        modif = ref_mean if np.isclose(mean_val, 0) else ref_mean / mean_val

        data[dwi_clusters[-1]] *= modif
        dwi_clusters = dwi_clusters[:-1]

    for i in range(len(dwi_clusters)):
        len_cl = dwi_clusters[i].stop - dwi_clusters[i].start
        weight = np.arange(len_cl).astype(float) / (len_cl - 1)
        if mean == B0PostProcess.batch:
            mean_val = np.mean(data[..., b0_clusters[i]])
            mean_val_p1 = np.mean(data[..., b0_clusters[i + 1]])
        else:
            mean_val = np.mean(data[..., b0_clusters[i].end - 1])
            mean_val_p1 = np.mean(data[..., b0_clusters[i + 1].start])

        modif = weight * mean_val_p1 + (1. - weight) * mean_val
        data[..., dwi_clusters[i]] *= ref_mean / modif

    for i in range(len(b0_clusters)):
        mean_cluster = np.mean(data[..., b0_clusters[i]])
        data[..., b0_clusters[i]] *= ref_mean / mean_cluster

    return data, ref_mean
