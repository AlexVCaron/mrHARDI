#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.t1mask2dwi_registration = true
params.topup_correction = true
params.eddy_correction = true
params.gaussian_noise_correction = true

include { extract_b0; squash_b0 } from '../modules/preprocess.nf'
include { dwi_denoise; prepare_topup; topup; prepare_eddy; eddy } from '../modules/denoise.nf'
include { ants_register; ants_transform } from '../modules/register.nf'
include { cat_datasets } from '../modules/utils.nf'

workflow preprocess_wkf {
    take: dwi_channel, rev_channel, t1_channel
    main:
        if ( params.t1mask2dwi_registration )
            dwi_channel.join(t1_mask_to_dwi_wkf(dwi_channel, t1_channel))

        if ( params.topup_correction )
            topup_channel = topup_wkf(dwi_channel, rev_channel)
        else
            topup_channel = Channel.empty()

        if ( params.eddy_correction )
            dwi_channel.join(eddy_wkf(dwi_channel, topup_channel))
        else
            if ( params.topup_correction )
                dwi_channel.join(apply_topup_wkf(dwi_channel, topup_channel))

        if ( params.gaussian_noise_correction )
            dwi_channel.join(dwi_denoise_wkf(dwi_channel))
    emit:
        dwi_channel
}

workflow t1_mask_to_dwi_wkf {
    take: dwi_channel, t1_channel
    main:
        extract_b0(dwi_channel) # This has to be parametrized
        ants_register(t1_channel.phase(extract_b0.out))
        ants_transform(t1_channel.phase(ants_register.out))
    emit:
        ants_transform.out
}

workflow topup_wkf {
    take: dwi_channel, rev_channel
    main:
        dwi_channel.phase(rev_channel) \
            | (prepare_topup & cat_datasets) \
            | join \
            | topup
    emit:
        topup.out
}

workflow eddy_wkf {
    take: dwi_channel, topup_channel
    main:
        squash_b0(cat_datasets(dwi_channel))
        prepare_eddy(topup_channel.phase(squash_b0.out))
        eddy(dwi_channel.phase(prepare_eddy.out))
    emit:
        eddy.out
}

workflow dwi_denoise_wkf {
    take: dwi_channel
    main:
        dwi_denoise(dwi_channel)
    emit:
        dwi_denoise.out
}
