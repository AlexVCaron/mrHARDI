#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.verbose_outputs = false

params.config.reconstruct.diamond = "$projectDir/.config/diamond.py"
params.config.reconstruct.dti = "$projectDir/.config/dti.py"
params.config.reconstruct.csd = "$projectDir/.config/csd.py"
params.config.reconstruct.response = "$projectDir/.config/response.py"

include { get_size_in_gb; prevent_sci_notation; uniformize_naming } from './functions.nf'

process diamond {
    memory { "${prevent_sci_notation(get_size_in_gb(input_dwi))} GB" }
    label "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(input_dwi), path(mask), path(data)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__diamond*.nii.gz"), emit: diamond
    script:
        if ( "${mask}" != "" )
            args += " --mask $mask"

        """
        magic-monkey diamond --in $input_dwi --mask $mask --out ${sid}__diamond --config $params.config.reconstruct.diamond
        """
}

process mrtrix_dti {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    label "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__dti_dti.nii.gz"), emit: dti
    script:
        args = "--in $dwi --bvals $bvals --bvecs $bvecs"
        if ( "${mask}" != "" )
            args += " --mask $mask"

        """
        magic-monkey dti $args --out ${sid}__dti --config $params.config.reconstruct.dti
        """
}

process response {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__response_*.txt"), emit: responses
    script:
        args = "--in $dwi --bvals $bvals --bvecs $bvecs"
        if ( "${mask}" != "" )
            args += " --mask $mask"

        """
        magic-monkey response $args --out ${sid}__response --config $params.config.reconstruct.response
        """
}

process csd {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    label "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(responses), path(dwi), path(bvals), path(bvecs), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__csd_*.nii.gz"), emit: odfs
    script:
        args = "--in $dwi --bvals $bvals --bvecs $bvecs"
        if ( "${mask}" == "" )
            args += " --mask $mask"

        """
        magic-monkey csd $args --out ${sid}__csd --responses ${responses.join(',')} --config $params.config.reconstruct.csd
        """
}
