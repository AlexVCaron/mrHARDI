#!/usr/bin/env nextflow

import java.io.File

nextflow.enable.dsl=2

params.config.register.ants_registration = "$projectDir/.config/ants_registration.py"
params.config.register.ants_motion = "$projectDir/.config/ants_motion.py"
params.config.register.ants_transform = "$projectDir/.config/ants_transform.py"

include { get_size_in_gb; swap_configurations } from '../functions.nf'

process ants_register {
    memory { get_size_in_gb(moving) + get_size_in_gb(target) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.register.ants_registration config.py"
    input:
        tuple val(sid), file(moving), file(target), val(reference), path(metadata)
        val(caller_name)
        file(config_overwrite)
    output:
        tuple val(sid), path("${sid}__registration_affine.mat"), path("${sid}__registration_rigid.nii.gz"), emit: affine
        tuple val(sid), path("${sid}__registration_ref.nii.gz"), emit: reference
        tuple val(sid), path("${sid}__registration_warped.nii.gz"), emit: image
        tuple val(sid), path("${sid}__registration*syn.nii.gz"), optional: true, emit: syn
        tuple val(sid), path("${sid}__registration_warped_metadata.*"), optional: true, emit: metadata
    script:
        config = swap_configurations("config.py", config_overwrite)

        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        magic-monkey ants_registration --moving ${moving.join(",")} --target ${target.join(",")} --out ${sid}__registration --config $config
        cp $reference ${sid}__registration_ref.nii.gz
        cp ${sid}__registration_warped.nii.gz ${sid}__registration_rigid.nii.gz
        mv ${sid}__registration0GenericAffine.mat ${sid}__registration_affine.mat
        if [ -f "${sid}__registration1Warp.nii.gz" ]
        then
            mv ${sid}__registration1Warp.nii.gz ${sid}__registration_syn.nii.gz
            mv ${sid}__registration1InverseWarp.nii.gz ${sid}__registration_inv_syn.nii.gz
        fi
        """
}

process ants_correct_motion {
    memory { get_size_in_gb(moving) + get_size_in_gb(target) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.register.ants_motion config.py"
    input:
        tuple val(sid), file(moving), file(target), path(metadata)
        val(caller_name)
        file(config_overwrite)
    output:
        tuple val(sid), path("${sid}__motion_correct_warped.nii.gz"), emit: image
        tuple val(sid), path("${sid}__motion_correct_warped_metadata.*"), optional: true, emit: metadata
    script:
        config = swap_configurations("config.py", config_overwrite)

        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        magic-monkey ants_motion --moving ${moving.join(",")} --target ${target.join(",")} --out ${sid}__motion_correct --config $config
        """
}

process ants_transform {
    memory { 2f * get_size_in_gb([img, ref]) }
    errorStrategy "finish"

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.register.ants_transform config.py"
    input:
        tuple val(sid), path(img), path(ref), path(affine), file(trans), file(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${img.simpleName}__transformed.nii.gz"), emit: image
        tuple val(sid), path("${img.simpleName}__transformed_metadata.*"), optional: true, emit: metadata
    script:
        args = "--in $img --ref $ref --mat $affine"
        if ( trans && !trans.empty() ) {
            args += " --trans ${trans}"
        }
        """
        magic-monkey ants_transform $args --out ${img.simpleName}__transformed.nii.gz --config config.py
        """
}
