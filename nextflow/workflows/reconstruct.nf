#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.recons_diamond = true
params.recons_dti = true
params.recons_csd = true

include { diamond; dti; csd; response } from '../modules/reconstruct.nf'
include { tournier2descoteaux_odf } from '../modules/utils.nf'

workflow reconstruct_wkf {
    take:
        dwi_channel
        mask_channel
        metadata_channel
    main:
        out_channels = []

        if ( params.recons_dti  ) {
            dti_wkf(dwi_channel, mask_channel)
            out_channels += [dti_wkf.out.dti]
        }
        else
            out_channels +=[null]

        if ( params.recons_csd  ) {
            csd_wkf(dwi_channel, mask_channel)
            out_channels += [csd_wkf.out.odfs]
        }
        else
            out_channels +=[null]

        if ( params.recons_diamond  ) {
            diamond_wkf(dwi_channel, mask_channel)
            out_channels += [diamond_wkf.out.diamond]
        }
        else
            out_channels +=[null]

    emit:
        dti = out_channels[0]
        csd = out_channels[1]
        diamond = out_channels[2]
        all = out_channels.subList(1, out_channels.size()).inject(out_channels[0]){ c, n -> c ? c.join(n, remainder: true) : c }
}

workflow csd_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        response(dwi_channel.join(mask_channel), "reconstruct")
        csd(response.out.responses.join(dwi_channel.join(mask_channel)), "reconstruct")
        // tournier2descoteaux_odf(csd.out.odfs, "reconstruct")
    emit:
        odfs = csd.out.odfs
        responses = response.out.responses
}

workflow dti_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        dti(dwi_channel.join(mask_channel), "reconstruct")
    emit:
        dti = dti.out.dti
}

workflow diamond_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        dwi_image = dwi_channel.map{ it.subList(0, 2) }
        other_files = dwi_channel.collect{ [it[0]] + it.subList(2, 4) }.map{ [it[0], it.subList(1, it.size())] }
        diamond(dwi_image.join(mask_channel).join(other_files), "reconstruct")
    emit:
        diamond = diamond.out.diamond
}
