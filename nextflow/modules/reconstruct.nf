#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.reconstruct.diamond = "$projectDir/.config/diamond.py"
params.config.reconstruct.dti = "$projectDir/.config/dti.py"
params.config.reconstruct.csd = "$projectDir/.config/csd.py"
params.config.reconstruct.response = "$projectDir/.config/response.py"

process diamond {
    input:
        tuple val(sid), val(input_prefix), path(mask)
    output:
        tuple val(sid), val("${sid}__diamond")
    script:
        """
        # Truncates the extension from the filename
        in=\$(echo ${input_prefix} | | sed 's/\\..*//g')
        magic-monkey diamond --in \$in --mask $mask --out ${sid}__diamond --config $params.config.reconstruct.diamond
        """
}

process dti {
    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
    output:
        tuple val(sid), path("${sid}__dti.nii.gz")
    script:
    args = "--in $dwi --bvals $bvals --bvecs $bvecs"
    if ( "${mask}" == "" )
        args += " --mask $mask"

    """
    magic-monkey dti $args --out ${sid}__dti.nii.gz --config $params.config.reconstruct.dti
    """
}

process csd {
    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs), path(mask)
    output:
        tuple val(sid), path("${sid}__csd.nii.gz")
    script:
    args = "--in $dwi --bvals $bvals --bvecs $bvecs"
    if ( "${mask}" == "" )
        args += " --mask $mask"

    """
    magic-monkey csd $args --out ${sid}__csd.nii.gz --config $params.config.reconstruct.csd
    """
}
