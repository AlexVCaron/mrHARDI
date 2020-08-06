#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.reconstruct.diamond = "../.config/diamond.py"
params.config.reconstruct.dti = "../.config/dti.py"
params.config.reconstruct.csd = "../.config/csd.py"

process diamond {
    input:
        tuple val(sid), val(input_prefix), path(mask)
    output:
        tuple val(sid), val("${sid}__diamond")
    script:
        """
        magic_monkey diamond $input_prefix $mask ${sid}__diamond --config $params.config.reconstruct.diamond
        """
}

process dti {
    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
    output:
        tuple val(sid), path("${sid}__dti.nii.gz")
    script:
    if ( "${mask}" == "")
        """
        magic_monkey dti $dwi $bvals $bvecs ${sid}__dti.nii.gz --config $params.config.reconstruct.dti
        """
    else
        """
        magic_monkey dti $dwi $bvals $bvecs ${sid}__dti.nii.gz --mask $mask --config $params.config.reconstruct.dti
        """
}

process csd {
    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
    output:
        tuple val(sid), path("${sid}__csd.nii.gz")
    script:
    if ( "${mask}" == "")
        """
        magic_monkey csd $dwi $bvals $bvecs ${sid}__csd.nii.gz --mask $mask --config $params.config.reconstruct.csd
        """
    else
        """
        magic_monkey csd $config $dwi $bvals $bvecs ${sid}__csd.nii.gz --config $params.config.reconstruct.csd
        """
}
