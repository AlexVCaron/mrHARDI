#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.register.ants_registration = "../.config/ants_registration.py"
params.config.register.ants_transform = "../.config/ants_transform.py"

process ants_register {
    input:
        tuple val(sid), file(moving), file(fixed)
    output:
        tuple val(sid), path("${sid}__registration_ref.nii.gz"), path("${sid}__registration_affine.mat")
    script:
        """
        magic_monkey ants_register --moving moving* --fixed fixed* --out ${sid}__registration --config $params.config.register.ants_registration
        """
}

process ants_transform {
    input:
        tuple val(sid), path(img), path(ref), path(affine)
    output:
        tuple val(sid), path("${sid}__transformed.nii.gz")
    script:
        """
        magic_monkey ants_transform $img $ref $affine ${sid}__transformed.nii.gz --config $params.config.register.ants_transform
        """
}
