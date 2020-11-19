#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.resampling_resolution = 1

include { get_size_in_gb } from '../functions.nf'

process scilpy_resample {
    memory { 2f * get_size_in_gb([image, mask]) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(image), file(mask), file(metadata)
        val(caller_name)
        val(interpolation)
    output:
        tuple val(sid), path("${image.getSimpleName()}_resampled.nii.gz"), emit: image
        tuple val(sid), path("${image.getSimpleName()}_resampled_metadata.py"), optional: true, emit: metadata
    script:
        after_script = ""
        if ( !metadata.empty() )
            after_script += "magic-monkey metadata --in ${image.getSimpleName()}_resampled.nii.gz --update_affine --metadata $metadata"
        """
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1
        export OMP_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        scil_resample_volume.py $image resampled.nii.gz --resolution $params.resampling_resolution --interp $interpolation
        fslmaths resampled.nii.gz -thr 0 ${image.getSimpleName()}_resampled.nii.gz
        $after_script
        """
}

process scilpy_resample_on_ref {
    memory { 2f * get_size_in_gb([image, ref, mask]) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(image), path(ref), file(mask), file(metadata)
        val(caller_name)
        val(interpolation)
    output:
        tuple val(sid), path("${image.getSimpleName()}_resampled.nii.gz"), emit: image
        tuple val(sid), path("${image.getSimpleName()}_resampled_metadata.py"), optional: true, emit: metadata
    script:
        after_script = ""
        if ( !mask.empty() ) {
            after_script = "magic-monkey apply_mask --in ${image.getSimpleName()}_resampled.nii.gz --out ${image.getSimpleName()}_resampled.nii.gz --mask $mask"
        }
        if ( !metadata.empty() )
            after_script += "\nmagic-monkey metadata --in ${image.getSimpleName()}_resampled.nii.gz --update_affine --metadata $metadata"
        """
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1
        export OMP_NUM_THREADS=1
        export OPENBLAS_NUM_THREADS=1
        scil_resample_volume.py $image resampled.nii.gz --ref $ref --enforce_dimensions --interp $interpolation
        fslmaths resampled.nii.gz -thr 0 ${image.getSimpleName()}_resampled.nii.gz
        $after_script
        """
}