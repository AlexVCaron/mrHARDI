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

    input:
        tuple val(sid), path(dwi), path(mask)
    output:
        tuple val(sid), path("${sid}__dwidenoise.nii.gz")
    script:
    if ( mask )
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz
        """
    else
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz --mask $mask
        """
}

process prepare_topup {
    beforeScript "cp $params.config.denoise.topup config.py"
    input:
        tuple val(sid), file(b0s), file(revs)
    output:
        tuple val(sid), path("${sid}__topup_script.sh"), path("${sid}__topup_acqp.txt"), path("${sid}__topup_config.cnf"), val("${sid}__topup")
    script:
        """
        magic-monkey topup --b0 $b0s --rev $revs --out ${sid}__topup --readout $params.acquisition.readout --config config.py
        """
}

process topup {
    memory { "${prevent_sci_notation(get_size_in_gb(b0))} GB" }
    cpus 1

    input:
        tuple val(sid), path(topup_script), path(topup_acqp), path(b0), path(mask)
    output:
        tuple val(sid), path("${sid}__topup.nii.gz"), path("${sid}__topup_field.nii.gz"), path("${sid}__topup_results_movpar.txt"), path("${sid}__topup_results_fieldcoef.nii.gz")
    script:
        args = "$topup_acqp $b0"
        if ( mask )
            args += " $mask"

        """
        ./$topup_script $args ${sid}__topup
        """
}

process apply_topup {
    memory { "${prevent_sci_notation(get_size_in_gb(image))} GB" }

    input:
        tuple val(sid), file(image), file(topup_params), val(topup_prefix)
    output:
        tuple val(sid), pat("${sid}__topup_corrected.nii.gz")
    script:
        """
        echo "Not Implemented Yet"
        """
}

process prepare_eddy {
    beforeScript "cp $params.config.denoise.eddy config.py"
    input:
        tuple val(sid), path(bvals), file(topup_acqp), file(rev_bvals)
    output:
        tuple val(sid), path("${sid}__eddy_script.sh"), path("${sid}__eddy_index.txt"), path("${sid}__eddy_acqp.txt")
    script:
        args = "--bvals $bvals"
        will_gen_acqp = true
        if ( !topup_acqp.empty() ) {
            args += " --acqp $topup_acqp"
            will_gen_acqp = false
        }
        else if ( !rev_bvals.empty() )
            args += " --rev $rev_bvals --readout $params.acquisition.readout"
        else
            args += " --readout $params.acquisition.readout"

        if ( params.use_cuda )
            args += " --cuda --config config.py"
        else
            args += " --config config.py"

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

    input:
        tuple val(sid), path(eddy_script), path(eddy_index), path(eddy_acqp), path(dwi), path(bvals), path(bvecs), path(mask)
    output:
        tuple val(sid), path("${sid}__eddy_corrected.nii.gz"), path("${sid}__eddy_corrected.bvecs")
    script:
        args = "$eddy_index $eddy_acqp $dwi $bvals $bvecs"
        if ( mask )
            args += " $mask"

        """
        ./$eddy_script $args ${sid}__eddy_corrected
        """
}
