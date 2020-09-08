#!/usr/bin/env nextflow

import java.io.File

nextflow.enable.dsl=2

params.config.register.ants_registration = "$projectDir/.config/ants_registration.py"
params.config.register.ants_transform = "$projectDir/.config/ants_transform.py"

process ants_register {
    beforeScript "cp $params.config.register.ants_registration config.py"
    input:
        tuple val(sid), file(moving), file(target)
    output:
        tuple val(sid), path("${sid}__registration_ref.nii.gz"), path("${sid}__registration_affine.mat")
    script:
        """
        magic-monkey ants_registration --moving $moving --target $target --out ${sid}__registration --config config.py
        """
}

process ants_transform {
    beforeScript "cp $params.config.register.ants_transform config.py"
    input:
        tuple val(sid), path(img), path(ref), path(affine)
    output:
        tuple val(sid), path("${sid}__transformed.nii.gz")
    script:
        """
        magic-monkey ants_transform --in $img --ref $ref --mat $affine --out ${sid}__transformed.nii.gz --config config.py
        """
}
