from numpy import concatenate


def concatenate_dwi(dwi_list, bvals_in, bvecs_in):
    return concatenate(dwi_list, axis=-1), \
           concatenate(bvals_in)[None, :] if bvals_in else None, \
           concatenate(bvecs_in, axis=1).T if bvecs_in else None
