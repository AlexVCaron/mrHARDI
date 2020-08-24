#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.preprocess.extract_b0 = "../.config/extract_b0.py"
params.config.preprocess.squash_b0 = "../.config/squash_b0.py"

process extract_b0 {
    input:
        tuple val(sid), path(dwi), path(bvals)
    output:
        tuple val(sid), path("${sid}__b0.nii.gz")
    script:
        """
        magic-monkey b0 extract --in $dwi --bvals $bvals --out ${sid}__b0 --config $params.config.preprocess.extract_b0
        """
}

process squash_b0 {
    input:
        tuple val(sid), path(dwi), path(bvals), path(bvecs)
    output:
        tuple val(sid), path("${sid}__b0_squashed.nii.gz"), path("${sid}__b0_squashed.bvals"), path("${sid}__b0_squashed.bvecs")
    script:
        """
        magic-monkey b0 squash --in $dwi --bvals $bvals --bvecs $bvecs --out ${sid}__b0_squashed --config $params.config.preprocess.squash_b0
        """
}
