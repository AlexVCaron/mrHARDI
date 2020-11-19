#!/usr/bin/env nextflow

nextflow.enable.dsl=2

//include { print_channel } from "./modules/debug.nf" // For debugging purpose only
include { load_dataset } from "./workflows/io.nf"
include { preprocess_wkf } from "./workflows/preprocess.nf"
include { reconstruct_wkf } from "./workflows/reconstruct.nf"
include { measure_wkf } from "./workflows/measure.nf"

workflow {
    dataloader = load_dataset()
    preprocess_wkf(dataloader.dwi, dataloader.rev, dataloader.anat, dataloader.metadata, dataloader.rev_metadata)
    reconstruct_wkf(preprocess_wkf.out.dwi, preprocess_wkf.out.mask, preprocess_wkf.out.metadata)
    // measure = measure_wkf(recons, dataloader.affine)
}
