#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.frf_fa = 0.7
params.frf_min_fa = 0.5
params.frf_min_nvox = 300
params.frf_roi_radius = 10


params.config.reconstruct.diamond = "$projectDir/.config/diamond.py"
params.config.reconstruct.dti = "$projectDir/.config/dti.py"
params.config.reconstruct.csd = "$projectDir/.config/csd.py"
params.config.reconstruct.response = "$projectDir/.config/response.py"

include { get_size_in_gb; uniformize_naming } from '../functions.nf'

process diamond {
    memory { 2f * get_size_in_gb([input_dwi, mask] + (data instanceof List ? data : [data])) }
    label "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/diamond", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

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
    memory { 2f * get_size_in_gb([dwi, mask]) }
    label "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/dti", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__dti_dti.nii.gz"), emit: dti
    script:
        args = "--in $dwi --bvals $bval --bvecs $bvec"
        if ( "${mask}" != "" )
            args += " --mask $mask"

        """
        magic-monkey dti $args --out ${sid}__dti --config $params.config.reconstruct.dti
        """
}

process response {
    memory { 2f * get_size_in_gb([dwi, mask]) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/fodf", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__response_*.txt"), emit: responses
    script:
        args = "--in $dwi --bvals $bval --bvecs $bvec"
        if ( "${mask}" != "" )
            args += " --mask $mask"

        """
        magic-monkey response $args --out ${sid}__response --config $params.config.reconstruct.response
        """
}

process csd {
    memory { 2.5 * get_size_in_gb([dwi, mask]) }
    label "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/fodf", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(responses), path(dwi), path(bval), path(bvec), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__csd_*.nii.gz"), emit: odfs
    script:
        args = "--in $dwi --bvals $bval --bvecs $bvec"
        if ( "${mask}" == "" )
            args += " --mask $mask"

        """
        magic-monkey csd $args --out ${sid}__csd --responses ${responses.join(',')} --config $params.config.reconstruct.csd
        """
}

process scilpy_response {
    memory { 2f * get_size_in_gb([dwi, mask]) }
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/fodf", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__response.txt"), emit: response
    script:
        """
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1
        export OMP_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        mrconvert -strides 1,2,3,4 -export_grad_fsl dwi4scil.bvec dwi4scil.bval -fslgrad $bvec $bval $dwi dwi4scil.nii.gz
        mrconvert -datatype uint8 -strides 1,2,3,4 $mask mask4scil.nii.gz
        scil_compute_ssst_frf.py dwi4scil.nii.gz dwi4scil.bval dwi4scil.bvec ${sid}__response.txt --mask mask4scil.nii.gz --fa $params.frf_fa --min_fa $params.frf_min_fa --min_nvox $params.frf_min_nvox --roi_radii $params.frf_roi_radius
        """
}

process scilpy_csd {
    memory { 2.5 * get_size_in_gb([dwi, mask]) }
    label "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/fodf", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(response), path(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__fodf.nii.gz"), emit: odfs
    script:
        """
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1
        export OMP_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        mrconvert -strides 1,2,3,4 -export_grad_fsl dwi4scil.bvec dwi4scil.bval -fslgrad $bvec $bval $dwi dwi4scil.nii.gz
        mrconvert -datatype uint8 -strides 1,2,3,4 $mask mask4scil.nii.gz
        scil_compute_ssst_fodf.py dwi4scil.nii.gz dwi4scil.bval dwi4scil.bvec $response ${sid}__fodf.nii.gz --mask mask4scil.nii.gz --force_b0_threshold --processes $task.cpus
        """
}
