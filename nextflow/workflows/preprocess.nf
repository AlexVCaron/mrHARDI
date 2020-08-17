#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { extract_b0; squash_b0 } from '../modules/preprocess.nf'
include { dwi_denoise; prepare_topup; topup; prepare_eddy; eddy } from '../modules/denoise.nf'
include { ants_register; ants_transform } from '../modules/register.nf'
include { cat_datasets } from '../modules/utils.nf'

workflow t1_mask_to_dwi {
    take: dwi_channel, t1_channel
    main:
        extract_b0(dwi_channel) # This has to be parametrized
        ants_register(t1_channel.phase(extract_b0.out))
        ants_transform(t1_channel.phase(ants_register.out))
    emit:
        mask = ants_transform.out
}

workflow topup {
    take: dwi_channel, rev_channel
    main:
        dwi_channel.phase(rev_channel) \
            | (prepare_topup & cat_datasets) \
            | phase \
            | topup
    emit:
        topup.out
}

workflow eddy {
    take: dwi_channel, topup_channel
    main:
        squash_b0(cat_datasets(dwi_channel))
        prepare_eddy(topup_channel.phase(squash_b0.out))
        eddy(dwi_channel.phase(prepare_eddy.out))
    emit:
        eddy.out
}
