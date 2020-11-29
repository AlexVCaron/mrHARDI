#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.eddy_on_rev = true
params.use_cuda = false
params.eddy_force_shelled = true


params.config.denoise.topup = "$projectDir/.config/topup.py"
params.config.denoise.eddy = "$projectDir/.config/eddy.py"
params.config.denoise.eddy_cuda = "$projectDir/.config/eddy_cuda.py"
params.config.denoise.n4 = "$projectDir/.config/n4_denoise.py"

include { get_size_in_gb; swap_configurations } from '../functions.nf'

process dwi_denoise {
    memory { 2f * get_size_in_gb([dwi, mask]) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), file(mask), file(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${dwi.simpleName}__dwidenoised.nii.gz"), emit: image
        tuple val(sid), path("${dwi.simpleName}__dwidenoised_metadata.*"), optional: true, emit: metadata
    script:
        after_denoise = "fslmaths -dt double dwidenoise.nii.gz -thr 0 ${dwi.simpleName}__dwidenoised.nii.gz -odt double\n"
        if ( !metadata.empty() )
            after_denoise += "cp $metadata ${dwi.simpleName}__dwidenoised_metadata.py"

        args = "-nthreads $task.cpus -datatype float64"
        if ( !mask.empty() )
            args += " -mask $mask"

        """
        dwidenoise $args $dwi dwidenoise.nii.gz
        $after_denoise
        """
}

process nlmeans_denoise {
    memory { 2f * get_size_in_gb(image) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(image)
        val(caller_name)
    output:
        tuple val(sid), path("${image.simpleName}__nlmeans_denoised.nii.gz"), emit: image
        tuple val(sid), path("${image.simpleName}__nlmeans_denoised_metadata.*"), optional: true, emit: metadata
    script:
        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        scil_run_nlmeans.py $image ${image.simpleName}__nlmeans_denoised.nii.gz 1 --processes $task.cpus -f
        """
}

process ants_gaussian_denoise {
    memory { 2f * get_size_in_gb([image, mask]) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(image), file(mask)
        val(caller_name)
    output:
        tuple val(sid), path("${image.simpleName}__ants_denoised.nii.gz"), emit: image
        tuple val(sid), path("${image.simpleName}__ants_denoised_metadata.*"), optional: true, emit: metadata
    script:
        args = ""
        if ( !mask.empty() )
            args += "--mask-image $mask"

        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        DenoiseImage --input-image $image --noise-model Gaussian --output [${image.simpleName}__ants_denoised.nii.gz,${image.simpleName}__ants_denoised_noise_map.nii.gz] --verbose 1 $args
        """
}

process n4_denoise {
    memory { 2f * get_size_in_gb([image, anat, mask]) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.denoise.n4 config.py"
    input:
        tuple val(sid), path(image), file(anat), file(mask), file(metadata)
        val(caller_name)
        file(config_overwrite)
    output:
        tuple val(sid), path("${image.simpleName}__n4denoised.nii.gz"), emit: image
        tuple val(sid), path("${image.simpleName}__n4denoised_metadata.*"), optional: true, emit: metadata
    script:
        config = swap_configurations(file("$workDir/config.py"), config_overwrite)

        after_denoise = ""
        args = ""
        if ( anat.empty() )
            args += "--in $image"
        else
            args += "--in $anat --apply $image"

        if ( !metadata.empty() ) {
            after_denoise += "mv n4denoise_metadata.py ${image.simpleName}__n4denoised_metadata.py\n"
            args += " --metadata $metadata"
        }
        after_denoise += "fslmaths -dt double n4denoise.nii.gz -thr 0 ${image.simpleName}__n4denoised.nii.gz -odt double\n"

        if ( !mask.empty() )
            args += " --mask $mask"

        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        magic-monkey n4 $args --out n4denoise --config $config
        $after_denoise
        """
}

process prepare_topup {
    errorStrategy "finish"

    beforeScript "cp $params.config.denoise.topup config.py"
    input:
        tuple val(sid), path(b0s), path(dwi_bval), path(rev_bval), file(metadata)
    output:
        tuple val(sid), path("${b0s.simpleName}__topup_script.sh"), path("${b0s.simpleName}__topup_acqp.txt"), path("${b0s.simpleName}__topup_config.cnf"), val("${b0s.simpleName}__topup_results"), emit: config
        tuple val(sid), path("${b0s.simpleName}__topup_metadata.*"), emit: metadata
        tuple val(sid), path("{${dwi_bval.simpleName},${rev_bval.simpleName}}_topup_indexes_metadata.*"), optional: true, emit : in_metadata_w_topup
    script:
        """
        magic-monkey topup --b0s $b0s --bvals $dwi_bval --rev_bvals $rev_bval --out ${b0s.simpleName}__topup --config config.py --verbose
        """
}

process topup {
    memory { 2f * get_size_in_gb(b0) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(topup_script), path(topup_acqp), path(topup_cnf), path(b0), path(output_metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${b0.simpleName}__topup.nii.gz"), emit: image
        tuple val(sid), path("${b0.simpleName}__topup_field.nii.gz"), emit: field
        tuple val(sid), path("${b0.simpleName}__topup_results_movpar.txt"), path("${b0.simpleName}__topup_results_fieldcoef.nii.gz"), emit: transfo
        tuple val(sid), path("${b0.simpleName}__topup.nii.gz"), path("${b0.simpleName}__topup_field.nii.gz"), path("${b0.simpleName}__topup_results_movpar.txt"), path("${b0.simpleName}__topup_results_fieldcoef.nii.gz"), emit: pkg
        tuple val(sid), path(output_metadata), optional: true, emit: metadata
    script:
        """
        ./$topup_script $b0 ${b0.simpleName}__topup
        """
}

process prepare_eddy {
    errorStrategy "finish"

    beforeScript params.use_cuda ? "cp $params.config.denoise.eddy_cuda config.py" : "cp $params.config.denoise.eddy config.py"
    input:
        tuple val(sid), val(prefix), file(topup_acqp), val(rev_prefix), path(data), path(metadata)
    output:
        tuple val(sid), path("${prefix}__eddy_script.sh"), path("${prefix}__eddy_index.txt"), path("${prefix}__eddy_acqp.txt"), emit: config
        tuple val(sid), path("${prefix}__eddy_slspec.txt"), emit: slspec, optional: true
        tuple val(sid), path("${sid}*non_zero.bvec"), emit: bvec, optional: true
        tuple val(sid), path("${prefix}__eddy_metadata.*"), emit: metadata, optional: true
    script:
        args = "--in $prefix --debug"
        will_gen_acqp = true
        if ( !topup_acqp.empty() ) {
            args += " --acqp $topup_acqp"
            will_gen_acqp = false
        }
        if ( rev_prefix ) {
            args += " --rev $rev_prefix"
        }

        if ( params.eddy_on_rev )
            args += " --rev_eddy"

        if ( params.use_cuda )
            args += " --cuda --config config.py"
        else
            args += " --config config.py"

        if ( params.eddy_force_shelled )
            args += " --shelled"

        if ( will_gen_acqp )
            """
            magic-monkey eddy $args --out ${prefix}__eddy
            """
        else
            """
            magic-monkey eddy $args --out ${prefix}__eddy && cp $topup_acqp "${prefix}__eddy_acqp.txt"
            """
}

process eddy {
    memory { 2f * get_size_in_gb([dwi, mask]) }
    label params.use_cuda ? "res_single_cpu" : "res_full_node"
    label params.use_cuda ? "res_gpu" : ""
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(eddy_script), path(eddy_index), path(eddy_acqp), file(eddy_slspec), path(dwi), path(bval), path(bvec), path(mask), val(topup_prefix), path(topup_package), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${dwi.simpleName}__eddy_corrected.nii.gz"), emit: dwi
        tuple val(sid), path("${dwi.simpleName}__eddy_corrected.bval"), emit: bval
        tuple val(sid), path("${dwi.simpleName}__eddy_corrected.bvec"), emit: bvec
        tuple val(sid), path("${dwi.simpleName}__eddy_corrected_metadata.py"), optional: true, emit: metadata
    script:
        after_script = ""
        if ( metadata )
            after_script += "cp $metadata ${dwi.simpleName}__eddy_corrected_metadata.py"

        args = "$dwi $bval $bvec"
        if ( mask )
            args += " $mask"

        args += " $eddy_acqp $eddy_index"

        if ( topup_prefix )
            args += " --topup $topup_prefix"

        if ( params.use_cuda )
            args += " --slspec $eddy_slspec"

        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        ./$eddy_script $args eddy_corrected
        mv eddy_corrected.eddy_rotated_bvecs ${dwi.simpleName}__eddy_corrected.bvec
        cp $bval ${dwi.simpleName}__eddy_corrected.bval
        fslmaths eddy_corrected.nii.gz -thr 0 ${dwi.simpleName}__eddy_corrected.nii.gz
        $after_script
        """
}

process gibbs_removal {
    memory { 2f * get_size_in_gb(dwi) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${dwi.simpleName}__gibbs_corrected.nii.gz"), emit: image
        tuple val(sid), path("${dwi.simpleName}__gibbs_corrected_metadata.*"), optional: true, emit: metadata
    script:
    after_denoise = "fslmaths -dt double gibbs_corrected.nii.gz -thr 0 ${dwi.simpleName}__gibbs_corrected.nii.gz -odt double\n"
    if ( metadata )
        after_denoise += "cp $metadata ${dwi.simpleName}__gibbs_corrected_metadata.py"

    """
    mrdegibbs -nthreads 1 -datatype float64 $dwi gibbs_corrected.nii.gz
    $after_denoise
    """
}