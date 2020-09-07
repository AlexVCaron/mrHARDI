#!/usr/bin/env nextflow

nextflow.enable.dsl=2

//include { print_channel } from "./modules/debug.nf" // For debugging purpose only
include { load_dataset } from "./workflows/io.nf"
include { preprocess_wkf } from "./workflows/preprocess.nf"
include { reconstruct_wkf } from "./workflows/reconstruct.nf"
include { measure_wkf } from "./workflows/measure.nf"

workflow {
    dataloader = load_dataset()
    dwi = preprocess_wkf(dataloader.dwi, dataloader.rev, dataloader.anat)
    // recons = reconstruct_wkf(dwi.collect{ it.subTuple(0, 4) }, dwi.collect{ new Tuple2(it[0], it[it.size() - 1]) })
    // measure = measure_wkf(recons, dataloader.affine)
}
