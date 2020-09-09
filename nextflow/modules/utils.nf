#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.utils.apply_mask = "$projectDir/.config/apply_mask.py"
params.config.utils.concatenate = "$projectDir/.config/cat.py"

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process apply_mask {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(img))} GB" }

    beforeScript "cp $params.config.utils.apply_mask config.py"
    input:
        tuple val(sid), path(img), path(mask)
    output:
        tuple val(sid), path("${sid}__masked.nii.gz")
    script:
        """
        magic-monkey apply_mask $img $mask ${sid}__masked.nii.gz --config config.py
        """
}

// TODO : Implement bet mask, if needed
process bet_mask {
    memory { "${prevent_sci_notation(get_size_in_gb(img))} GB" }

    input:
        tuple val(sid), path(img)
    output:
        tuple val(sid), path("${sid}__bet_mask.nii.gz")
    script:
        """
        magic-monkey bet $img ${sid}__bet_mask.nii.gz
        """
}

process cat_datasets {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(imgs))} GB" }
    cpus 1

    beforeScript "cp $params.config.utils.concatenate config.py"
    input:
        tuple val(sid), file(imgs), file(bvals), file(bvecs)
    output:
        tuple val(sid), file("${sid}__concatenated.*")
    script:
        args = "--in $imgs"

        if ( bvals.size() > 0 )
            args += "--bvals $bvals"
        if ( bvecs.size() > 0 )
            args += "--bvecs $bvecs"

        println "$args"
        """
        magic-monkey concatenate $args --out ${sid}__concatenated --config config.py
        """
}
