#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.measure.fa_from_dti = "../.config/fa_from_dti.py"

process fa_from_dti {
    input:
        tuple val(sid), path(dti), path(mask)
    output:
        tuple val(sid), path("${sid}__fa.nii.gz")
    script:
    if
        """
        magic_monkey fa_from_dti $dti $mask ${sid}__fa.nii.gz --config $params.config.measure.fa_from_dti
        """
}
