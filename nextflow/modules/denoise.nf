#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.denoise.topup = "../.config/topup.py"
params.config.denoise.eddy = "../.config/eddy.py"

process dwi_denoise {
    input:
        tuple val(sid), path(dwi), path(mask)
    output:
        tuple val(sid), path("${sid}__dwidenoise.nii.gz")
    script:
    if ( "${mask}" == "")
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz
        """
    else
        """
        dwidenoise $dwi ${sid}__dwidenoise.nii.gz --mask $mask
        """
}

process prepare_topup {
    input:
        tuple val(sid), file(b0s), file(revs)
    output:
        tuple val(sid), path("${sid}__topup_script.sh"), path("${sid}__topup_acqp.txt"), path("${sid}__topup_config.txt")
    script:
        """
        magic_monkey topup --b0 $b0s --rev $revs --out ${sid}__topup --config $params.config.denoise.topup
        """
}

process topup {
    input:
        tuple val(sid), path(dwi), path(mask), path(topup_script), path(topup_params)
    output:
        tuple val(sid), path("${sid}__topup.nii.gz")
    script:
        """
        ./$topup_script $topup_params $dwi $mask ${sid}__topup.nii.gz
        """
}

process prepare_eddy {
    input:
        tuple val(sid), path(bvals), path(topup_params)
    output
        tuple val(sid), path("${sid}__eddy_script.sh"), path("${sid}__eddy_params.txt")
    script:
        """
        magic_monkey eddy_prep $bvals $topup_params ${sid}__eddy --config $params.config.denoise.eddy
        """
}

process eddy {
    input:
        tuple val(sid), path(dwi), path(mask), path(bvals), path(bvecs), path(eddy_script), path(eddy_params), path(topup_params)
    output:
        tuple val(sid), path("${sid}__eddy_corrected.nii.gz"), path("${sid}__eddy_corrected.bvals"), path("${sid}__eddy_corrected.bvecs")
    script:
        """
        ./$eddy_script $eddy_params $topup_params $dwi $bvals $bvecs $mask ${sid}__eddy_corrected
        """
}
