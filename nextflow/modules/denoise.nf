#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.denoise.topup = "$projectDir/.config/topup.py"
params.config.denoise.eddy = "$projectDir/.config/eddy.py"
params.config.denoise.eddy_cuda = "$projectDir/.config/eddy_cuda.py"

params.use_cuda = false
params.topup_correction = true
params.rev_is_b0 = true

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process dwi_denoise {
    memory { "${prevent_sci_notation(get_size_in_gb(dwi))} GB" }
    cpus 1

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(mask), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__dwidenoise.nii.gz"), emit: image
        tuple val(sid), path("${sid}__dwidenoise_metadata.*"), optional: true, emit: metadata
    script:
    after_denoise = ""
    if ( metadata )
        after_denoise += "cp $metadata ${sid}__dwidenoise_metadata.py"

    if ( mask )
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz
        $after_denoise
        """
    else
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz --mask $mask
        $after_denoise
        """
}

process prepare_topup {
    beforeScript "cp $params.config.denoise.topup config.py"
    input:
        tuple val(sid), file(b0s), file(revs), path(metadata)
    output:
        tuple val(sid), path("${sid}__topup_script.sh"), path("${sid}__topup_acqp.txt"), path("${sid}__topup_config.cnf"), val("${sid}__topup_results"), emit: config
        tuple val(sid), path("${sid}__topup_metadata.*"), emit: metadata
    script:
        """
        magic-monkey topup --b0 $b0s --rev $revs --out ${sid}__topup --config config.py
        """
}

process topup {
    memory { "${prevent_sci_notation(get_size_in_gb(b0))} GB" }
    cpus 1

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), path(topup_script), path(topup_acqp), path(topup_cnf), path(b0), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__topup.nii.gz"), emit: image
        tuple val(sid), path("${sid}__topup_field.nii.gz"), emit: field
        tuple val(sid), path("${sid}__topup_results_movpar.txt"), path("${sid}__topup_results_fieldcoef.nii.gz"), emit: transfo
        tuple val(sid), path("${sid}__topup.nii.gz"), path("${sid}__topup_field.nii.gz"), path("${sid}__topup_results_movpar.txt"), path("${sid}__topup_results_fieldcoef.nii.gz"), emit: pkg
        tuple val(sid), path(metadata), optional: true, emit: metadata
    script:
        """
        ./$topup_script $b0 ${sid}__topup
        """
}

process apply_topup {
    memory { "${prevent_sci_notation(get_size_in_gb(image))} GB" }

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), file(image), file(topup_params), val(topup_prefix), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__topup_corrected.nii.gz"), emit: image
        tuple val(sid), path("${sid}__topup_corrected_metadata.*"), optional: true, emit: metadata
    script:
        """
        echo "Not Implemented Yet"
        """
}

process prepare_eddy {
    beforeScript params.use_cuda ? "cp $params.config.denoise.eddy_cuda config.py" : "cp $params.config.denoise.eddy config.py"
    input:
        tuple val(sid), path(bvals), file(topup_acqp), file(rev_bvals), path(metadata)
    output:
        tuple val(sid), path("${sid}__eddy_script.sh"), path("${sid}__eddy_index.txt"), path("${sid}__eddy_acqp.txt"), emit: config
        tuple val(sid), path("${sid}__eddy_metadata.*"), emit: metadata
    script:
        prefix = "$bvals".tokenize(".")[0]
        args = "--in $prefix"
        will_gen_acqp = true
        if ( !topup_acqp.empty() ) {
            args += " --acqp $topup_acqp"
            will_gen_acqp = false
        }
        if ( !rev_bvals.empty() ) {
            prefix = "$rev_bvals".tokenize(".")[0]
            args += " --rev $prefix"
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

    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), path(eddy_script), path(eddy_index), path(eddy_acqp), path(dwi), path(bvals), path(bvecs), path(mask), val(topup_prefix), path(topup_package), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__eddy_corrected.nii.gz"), emit: dwi
        tuple val(sid), path("${sid}__eddy_corrected.bvecs"), emit: bvecs
        tuple val(sid), path(metadata), optional: true, emit: metadata
    script:
        args = "$dwi $bvals $bvecs"
        if ( mask )
            args += " $mask"

        args += " $eddy_acqp $eddy_index"

        if ( topup_prefix )
            args += " --topup $topup_prefix"

        """
        ./$eddy_script $args ${sid}__eddy_corrected
        mv ${sid}__eddy_corrected.eddy_rotated_bvecs ${sid}__eddy_corrected.bvecs
        cp $bvals ${sid}__eddy_corrected.bvals
        """
}
