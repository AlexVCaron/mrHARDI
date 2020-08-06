#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { t1_mask_to_dwi } from 'workflows/preprocess.nf'

workflow {
    channel.from([])
}