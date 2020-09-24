#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.recons_diamond = true
params.recons_dti = true
params.recons_csd = true

include { diamond; dti; csd } from '../modules/reconstruct.nf'

workflow reconstruct_wkf {
    take:
        dwi_channel
        mask_channel
        metadata_channel
    main:
        out_channels = [
            params.recons_dti ? dti_wkf(dwi_channel, mask_channel) : null,
            params.recons_csd ? csd_wkf(dwi_channel, mask_channel) : null,
            params.recons_diamond ? diamond_wkf(dwi_channel, mask_channel) : null
        ]
    emit:
        dti = out_channels[0]
        csd = out_channels[1]
        diamond = out_channels[2]
}

workflow csd_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        csd(dwi_channel.join(mask_channel), "reconstruct")
    emit:
        csd.out
}

workflow dti_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        dti(dwi_channel.join(mask_channel), "reconstruct")
    emit:
        dti.out
}

workflow diamond_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        diamond(dwi_channel.collect{ it.subList(0, 2) }.join(mask_channel), "reconstruct")
    emit:
        diamond.out
}
