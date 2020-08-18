#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.recons_diamond = true
params.recons_dti = true
params.recons_csd = true

include { diamond; dti; csd } from '../modules/reconstruct.nf'

workflow reconstruct_wkf {
    take: dwi_channel, mask_channel
    main:
        out_channel = Channel.empty()
        if ( params.recons_dti )
            out_channel.join(dti_wkf(dwi_channel, mask_channel))
        if ( params.recons_csd )
            out_channel.join(csd_wkf(dwi_channel, mask_channel))
        if ( params.recons_diamond )
            out_channel.join(diamond_wkf(dwi_channel, mask_channel))
    emit:
        out_channel
}

workflow csd_wkf {
    take: dwi_channel, mask_channel
    main:
        csd(dwi_channel.join(mask_channel))
    emit:
        csd.out
}

workflow dti_wkf {
    take: dwi_channel, mask_channel
    main:
        dti(dwi_channel.join(mask_channel))
    emit:
        dti.out
}

workflow diamond_wkf {
    take: dwi_channel, mask_channel
    main:
        diamond(dwi_channel.collect{ it.subTuple(0, 2) }.join(mask_channel))
    emit:
        diamond.out
}
