#!/usr/bin/env nextflow

import java.io.File

nextflow.enable.dsl=2

params.config.register.ants_registration = "$projectDir/.config/ants_registration.py"
params.config.register.ants_transform = "$projectDir/.config/ants_transform.py"

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process ants_register {
    memory { "${prevent_sci_notation(get_size_in_gb(moving) + get_size_in_gb(target))} GB" }
    label "res_full_node"

    beforeScript "cp $params.config.register.ants_registration config.py"
    input:
        tuple val(sid), file(moving), file(target)
    output:
        tuple val(sid), path("${sid}__registration_ref.nii.gz"), path("${sid}__registration_affine.mat"), path("${sid}__registration*syn.nii.gz")
    script:
        """
        magic-monkey ants_registration --moving $moving --target $target --out ${sid}__registration --config config.py
        mv ${sid}__registration_warped.nii.gz ${sid}__registration_ref.nii.gz
        mv ${sid}__registration0GenericAffine.mat ${sid}__registration_affine.mat
        if [ -f "${sid}__registration1Warp.nii.gz" ]
        then
            mv ${sid}__registration1Warp.nii.gz ${sid}__registration_syn.nii.gz
            mv ${sid}__registration1InverseWarp.nii.gz ${sid}__registration_inv_syn.nii.gz
        fi
        """
}

process ants_transform {
    memory { "${prevent_sci_notation(get_size_in_gb(img) * 2f)} GB" }

    beforeScript "cp $params.config.register.ants_transform config.py"
    input:
        tuple val(sid), path(img), path(ref), path(affine), path(trans)
    output:
        tuple val(sid), path("${sid}__transformed.nii.gz")
    script:
        args = "--in $img --ref $ref --mat $affine"
        if ( trans && !trans.empty() ) {
            args += " --trans ${trans}"

        }
        """
        magic-monkey ants_transform $args --out ${sid}__transformed.nii.gz --config config.py
        """
}
