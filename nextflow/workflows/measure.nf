#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.recons_diamond = true
params.recons_dti = true
params.recons_csd = true

params.config.workflow.dti_for_odf_metrics = file("$projectDir/.config/.workflow/dti_for_odf_metrics.py")

include { dti_metrics; dti_metrics as dti_for_odfs_metrics; diamond_metrics; odf_metrics } from '../modules/measure.nf'
include { uniformize_naming; replace_naming_to_underscore } from '../modules/functions.nf'
include { dti_wkf } from './reconstruct.nf'

workflow measure_wkf {
    take:
        dwi_channel
        data_channel
        mask_channel
        metadata_channel
    main:
        dti_channel = Channel.empty()
        diamond_channel = Channel.empty()
        odfs_channel = Channel.empty()
        data_dti = Channel.empty()

        if ( params.recons_dti ) {
            data_dti = data_channel.map{ [it[0], it[1]] }
            metadata_dti = uniformize_naming(metadata_channel, "dti_metadata", false)
            mask_dti = uniformize_naming(mask_channel, "dti_mask", false)
            prefix_dti = data_dti.map{ [it[0], "${it[0]}__dti"] }
            dti_metrics(prefix_dti.join(mask_dti).join(data_dti).join(metadata_dti), "measure", "")
            dti_channel = dti_metrics.out.metrics
        }

        if ( params.recons_diamond ) {
            data = data_channel.map{ [it[0], it[3]] }
            metadata = uniformize_naming(metadata_channel, "diamond_metadata", false)
            mask_diamond = uniformize_naming(mask_channel, "diamond_mask", false)
            prefix_channel = data.map{ [it[0], "${it[0]}__diamond"] }
            diamond_metrics(prefix_channel.join(mask_diamond).join(data).join(metadata), "measure")
            diamond_channel = diamond_metrics.out.metrics
        }

        if ( params.recons_csd ) {
            if ( !params.recons_dti ) {
                dti_wkf(dwi_channel, mask_channel)
                data_dti = dti_wkf.out.dti
            }

            metadata_dti = uniformize_naming(metadata_channel, "dti_metadata", false)
            mask_dti = uniformize_naming(mask_channel, "dti_mask", false)
            prefix_dti = data_dti.map{ [it[0], "${it[0]}__dti"] }
            dti_for_odfs_metrics(
                prefix_dti.join(mask_dti).join(data_dti).join(metadata_dti),
                "measure", params.config.workflow.dti_for_odf_metrics
            )
            data = data_channel.map{ [it[0], it[2]] }.join(dti_for_odfs_metrics.out.metrics).map{ it.flatten() }

            mask_odfs = uniformize_naming(mask_channel, "desc07_odf_mask", false)
            odf_metrics(data.join(mask_odfs), "measure")
            odfs_channel = odf_metrics.out.metrics
        }
    emit:
        metrics = dti_channel.join(diamond_channel)
        dti = dti_channel
        diamond = diamond_channel
        odfs = odfs_channel
}
