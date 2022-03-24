#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.preprocess.extract_b0 = "$projectDir/.config/extract_b0_mean.py"
params.config.preprocess.squash_b0 = "$projectDir/.config/squash_b0.py"

include { get_size_in_gb; swap_configurations } from '../functions.nf'

process extract_b0 {
    memory { 2f * get_size_in_gb(dwi) }
    label "res_single_cpu"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript { "cp $params.config.preprocess.extract_b0 config.py" }
    input:
        tuple val(sid), path(dwi), path(bval), path(metadata)
        val(suffix)
        val(caller_name)
        file(config_overwrite)
    output:
        tuple val(sid), path("${dwi.simpleName}__b0${suffix}.nii.gz"), emit: b0
        tuple val(sid), path("${dwi.simpleName}__b0*_metadata.*"), optional: true, emit: metadata
    script:
        config = swap_configurations("config.py", config_overwrite)

        """
        magic-monkey b0 extract --in $dwi --bvals $bval --out ${dwi.simpleName}__b0${suffix} --config $config
        """
}

process squash_b0 {
    memory { 2f * get_size_in_gb(dwi) }
    label "res_single_cpu"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(metadata)
        val(suffix)
        val(caller_name)
    output:
        tuple val(sid), path("${dwi.simpleName}__b0${suffix}_squashed.nii.gz"), path("${dwi.simpleName}__b0${suffix}_squashed.bval"), path("${dwi.simpleName}__b0${suffix}_squashed.bvec"), emit: dwi
        tuple val(sid), path("${dwi.simpleName}__b0${suffix}_squashed_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey b0 squash --in $dwi --bvals $bval --bvecs $bvec --out ${dwi.simpleName}__b0${suffix}_squashed --config $params.config.preprocess.squash_b0
        """
}
