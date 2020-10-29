#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.denoise.topup = "$projectDir/.config/topup.py"
params.config.denoise.eddy = "$projectDir/.config/eddy.py"
params.config.denoise.eddy_cuda = "$projectDir/.config/eddy_cuda.py"
params.config.denoise.n4 = "$projectDir/.config/n4_denoise.py"

params.use_cuda = false
params.topup_correction = true
params.rev_is_b0 = true

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process dwi_denoise {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), file(mask), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__dwidenoise.nii.gz"), emit: image
        tuple val(sid), path("${sid}__dwidenoise_metadata.*"), optional: true, emit: metadata
    script:
    after_denoise = "fslmaths -dt double dwidenoise.nii.gz -thr 0 ${sid}__dwidenoise.nii.gz -odt double\n"
    if ( metadata )
        after_denoise += "cp $metadata ${sid}__dwidenoise_metadata.py"

    if ( !mask.empty() )
        """
        dwidenoise -mask $mask -datatype float64 $dwi dwidenoise.nii.gz
        $after_denoise
        """
    else
        """
        dwidenoise -datatype float64 $dwi dwidenoise.nii.gz
        $after_denoise
        """
}

process n4_denoise {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    label "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.denoise.n4 config.py"
    input:
        tuple val(sid), path(dwi), file(mask), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__n4denoise.nii.gz"), emit: image
        tuple val(sid), path("${sid}__n4denoise_metadata.*"), optional: true, emit: metadata
    script:
    after_denoise = "fslmaths -dt double n4denoise.nii.gz -thr 0 ${sid}__n4denoise.nii.gz -odt double\n"
    if ( metadata )
        after_denoise += "cp $metadata ${sid}__n4denoise_metadata.py"

    if ( !mask.empty() )
        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        magic-monkey n4 --in $dwi --out n4denoise --mask $mask --config config.py
        $after_denoise
        """
    else
        """
        export OMP_NUM_THREADS=$task.cpus
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=$task.cpus
        export OPENBLAS_NUM_THREADS=1
        magic-monkey n4 --in $dwi --out n4denoise --config config.py
        $after_denoise
        """
}

process prepare_topup {
    beforeScript "cp $params.config.denoise.topup config.py"
    input:
        tuple val(sid), path(b0s), path(revs), file(metadata)
    output:
        tuple val(sid), path("${sid}__topup_script.sh"), path("${sid}__topup_acqp.txt"), path("${sid}__topup_config.cnf"), val("${sid}__topup_results"), emit: config
        tuple val(sid), path("${sid}__topup_metadata.*"), emit: metadata
        tuple val(sid), path("${sid}__*_topup_indexes_metadata.*"), optional: true, emit : in_metadata_w_topup
    script:
        """
        magic-monkey topup --bvals $b0s --rev $revs --out ${sid}__topup --config config.py
        """
}

process topup {
    memory { "${prevent_sci_notation(get_size_in_gb(b0))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(topup_script), path(topup_acqp), path(topup_cnf), path(b0), path(output_metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__topup.nii.gz"), emit: image
        tuple val(sid), path("${sid}__topup_field.nii.gz"), emit: field
        tuple val(sid), path("${sid}__topup_results_movpar.txt"), path("${sid}__topup_results_fieldcoef.nii.gz"), emit: transfo
        tuple val(sid), path("${sid}__topup.nii.gz"), path("${sid}__topup_field.nii.gz"), path("${sid}__topup_results_movpar.txt"), path("${sid}__topup_results_fieldcoef.nii.gz"), emit: pkg
        tuple val(sid), path(output_metadata), optional: true, emit: metadata
    script:
        """
        ./$topup_script $b0 ${sid}__topup
        """
}

process prepare_eddy {
    beforeScript params.use_cuda ? "cp $params.config.denoise.eddy_cuda config.py" : "cp $params.config.denoise.eddy config.py"
    input:
        tuple val(sid), val(prefix), file(topup_acqp), val(rev_prefix), path(data), path(metadata)
    output:
        tuple val(sid), path("${sid}__eddy_script.sh"), path("${sid}__eddy_index.txt"), path("${sid}__eddy_acqp.txt"), emit: config
        tuple val(sid), path("${sid}__eddy_slspec.txt"), emit: slspec, optional: true
        tuple val(sid), path("${sid}__eddy_metadata.*"), emit: metadata
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
            magic-monkey eddy $args --out ${sid}__eddy
            """
        else
            """
            magic-monkey eddy $args --out ${sid}__eddy && cp $topup_acqp "${sid}__eddy_acqp.txt"
            """
}

process eddy {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    label "res_full_node"
    label params.use_cuda ? "res_gpu" : ""

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(eddy_script), path(eddy_index), path(eddy_acqp), file(eddy_slspec), path(dwi), path(bvals), path(bvecs), path(mask), val(topup_prefix), path(topup_package), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__eddy_corrected.nii.gz"), emit: dwi
        tuple val(sid), path("${sid}__eddy_corrected.bvecs"), emit: bvecs
        tuple val(sid), path("${sid}__eddy_corrected_metadata.py"), optional: true, emit: metadata
    script:
        after_script = ""
        if ( metadata )
            after_script += "cp $metadata ${sid}__eddy_corrected_metadata.py"

        args = "$dwi $bvals $bvecs"
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
        mv eddy_corrected.eddy_rotated_bvecs ${sid}__eddy_corrected.bvecs
        cp $bvals ${sid}__eddy_corrected.bvals
        fslmaths eddy_corrected.nii.gz -thr 0 ${sid}__eddy_corrected.nii.gz
        $after_script
        """
}
