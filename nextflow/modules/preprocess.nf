#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.preprocess.extract_b0 = "$projectDir/.config/extract_b0.py"
params.config.preprocess.squash_b0 = "$projectDir/.config/squash_b0.py"

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process extract_b0 {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(dwi))} GB" }

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bvals), path(metadata)
        val(suffix)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__b0${suffix}.nii.gz"), emit: b0
        tuple val(sid), path("${sid}__b0*_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey b0 extract --in $dwi --bvals $bvals --out ${sid}__b0${suffix} --config $params.config.preprocess.extract_b0
        """
}

process squash_b0 {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(dwi))} GB" }

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(metadata)
        val(suffix)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__b0${suffix}_squashed.nii.gz"), path("${sid}__b0${suffix}_squashed.bvals"), path("${sid}__b0${suffix}_squashed.bvecs"), emit: dwi
        tuple val(sid), path("${sid}__b0${suffix}_squashed_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey b0 squash --in $dwi --bvals $bvals --bvecs $bvecs --out ${sid}__b0${suffix}_squashed --config $params.config.preprocess.squash_b0
        """
}
