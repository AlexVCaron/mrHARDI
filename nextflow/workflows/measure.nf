#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.measure_diamond = true
params.measure_dti = true

include { dti_metrics; diamond_metrics } from '../modules/measure.nf'

workflow measure_wkf {
    take:
        data_channel
        metadata_channel
    main:
        dti_channel = Channel.empty()
        diamond_channel = Channel.empty()

        in_channel = data_channel.map { new Tuple2(it[0], it[1].split('.')[0]) }
        in_channel.join(metadata_channel)

        if ( params.measure_dti )
            dti_channel = dti_metrics(in_channel, "measure").out
        if ( params.measure_diamond )
            diamond_channel = diamond_metrics(in_channel, "measure").out
    emit:
        metrics = dti_channel.join(diamond_channel)
        dti = dti_channel
        diamond = diamond_channel
}
