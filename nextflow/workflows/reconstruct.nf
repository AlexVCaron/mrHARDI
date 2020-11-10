#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.recons_diamond = true
params.recons_dti = true
params.recons_csd = true

params.reconstruct_use_mrtrix = false

params.convert_tournier2descoteaux = true

include { diamond; mrtrix_dti; csd; response } from '../modules/reconstruct.nf'
include { scil_dti_and_metrics } from '../modules/measure.nf'
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
        all = out_channels.subList(1, out_channels.size()).inject(out_channels[0]){ c, n -> n ? c.join(n, remainder: true) : c }
}

workflow csd_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        response(dwi_channel.join(mask_channel), "reconstruct")
        csd(response.out.responses.join(dwi_channel.join(mask_channel)), "reconstruct")
        csd_channel = csd.out.odfs
        if ( params.convert_tournier2descoteaux ) {
            tournier2descoteaux_odf(csd.out.odfs, "reconstruct")
            csd_channel = tournier2descoteaux_odf.out.odfs
        }
    emit:
        odfs = csd_channel
        responses = response.out.responses
}

workflow dti_wkf {
    take:
        dwi_channel
        mask_channel
    main:
        dti_output = Channel.empty()
        if ( params.reconstruct_use_mrtrix ) {
            mrtrix_dti(dwi_channel.join(mask_channel), "reconstruct")
            dti_output = mrtrix_dti.out.dti
        }
        else {
            scil_dti_and_metrics(dwi_channel.join(mask_channel), "reconstruct", "measure")
            dti_output = scil_dti_and_metrics.out.dti
        }
    emit:
        dti = dti_output
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
