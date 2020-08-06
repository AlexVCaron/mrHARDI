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


def mean_b0_clusters(b0_vol, mask, output_shape):
    b0_clusters = np.ma.notmasked_contiguous(mask, axis=0)
    output_vol = np.zeros(output_shape + (0,))
    for cluster in b0_clusters:
        output_vol = np.concatenate((
            output_vol,
            np.mean(b0_vol[..., cluster].reshape(output_shape + (-1,)), axis=-1)[..., None]
        ), axis=-1)

    return output_vol


def extract_b0(dwi_vol, bvals, b0_strides=None, mean=B0PostProcess.none):
    b0_mask = np.isclose(bvals, 0)

    if b0_strides:
        print("Extracting b0 volumes at each {} volumes".format(b0_strides))
        b0_mask[:dwi_vol.shape[-1]] = pick_b0(b0_mask[:dwi_vol.shape[-1]], b0_strides)

    print("Masking b0 based on mask")

    b0_vol = dwi_vol[..., b0_mask[:dwi_vol.shape[-1]]]

    print("Found {} b0 volumes in dataset".format(b0_vol.shape[-1]))

    if mean is B0PostProcess.batch:
        print("Applying mean to b0 in batch")
        mask = np.ma.masked_array(b0_mask)
        mask[~b0_mask] = np.ma.masked
        b0_vol = mean_b0_clusters(dwi_vol, mask, dwi_vol.shape[:-1])
        print("Found {} mean b0 volumes in dataset".format(b0_vol.shape[-1]))
    elif mean is B0PostProcess.whole:
        print("Applying mean to whole b0 volume")
        b0_vol = np.mean(b0_vol, axis=-1)[..., None]

    return b0_vol


def squash_b0(dwi_vol, bvals, bvecs, mean=B0PostProcess.batch):
    b0_mask = np.isclose(bvals, 0)
    mask = np.ma.masked_array(b0_mask)
    mask[~b0_mask] = np.ma.masked

    if mean is B0PostProcess.whole:
        b0 = extract_b0(dwi_vol, bvals, mean=mean)
        return np.hstack((b0, dwi_vol[~b0_mask])), bvals[~b0_mask], bvecs[~b0_mask]

    b0_clusters = list(np.ma.notmasked_contiguous(mask, axis=0))
    dwi_clusters = list(np.ma.clump_masked(mask))

    output_shape = dwi_vol.shape[:-1] + (dwi_vol.shape[-1] + len(b0_clusters) - np.sum(b0_mask),)
    data = np.zeros(output_shape)
    out_bvals = []
    out_bvecs = []

    if mean is B0PostProcess.none:
        b0_extractor = lambda cluster: cluster[..., 0]
    else:
        b0_extractor = lambda cluster: np.mean(cluster, axis=-1)

    shape_reduc = 0
    for i in range(len(dwi_clusters)):
        data[..., b0_clusters[i].start - shape_reduc] = b0_extractor(dwi_vol[..., b0_clusters[i]])
        out_bvals.append(0)
        out_bvecs.append([1, 0, 0])
        shape_reduc += b0_clusters[i].stop - b0_clusters[i].start - 1
        data_slice = slice(dwi_clusters[i].start - shape_reduc, dwi_clusters[i].stop - shape_reduc)
        data[..., data_slice] = dwi_vol[..., dwi_clusters[i]]
        out_bvals += bvals[dwi_clusters[i]].tolist()
        out_bvecs += bvecs[:, dwi_clusters[i]].T.tolist()

    if len(b0_clusters) > len(dwi_clusters):
        data[..., -1] = b0_extractor(dwi_vol[..., b0_clusters[-1]])
        out_bvals.append(0)
        out_bvecs.append([0, 0, 0])

    return data, np.array(out_bvals)[None, ...], np.array(out_bvecs).T
