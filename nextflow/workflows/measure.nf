#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.measure_diamond = true
params.measure_dti = true

include { dti_metrics; diamond_metrics } from '../modules/measure.nf'

process measure_wkf {
    take: dwi_channel, affine_channel
    main:
        out_channel = Channel.empty()
        in_channel = dwi_channel.map { new Tuple2(it[0], it[1].split('.')[0]) }
        in_channel.join(affine_channel)

        if ( params.measure_dti )
            out_channel.join(dti_metrics(in_channel))
        if ( params.measure_diamond )
            out_channel.join(diamond_metrics(in_channel))
    emit:
        out_channel
}
