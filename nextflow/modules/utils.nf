#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.utils.apply_mask = "../.config/apply_mask.py"
params.config.utils.concatenate = "../.config/cat.py"

process apply_mask {
    input:
        tuple val(sid), path(img), path(mask)
    output:
        tuple val(sid), path("${sid}__masked.nii.gz")
    script:
        """
        magic-monkey apply_mask $img $mask ${sid}__masked.nii.gz --config $params.config.utils.apply_mask
        """
}

// TODO : Implement bet mask, if needed
process bet_mask {
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
        magic-monkey concatenate $args --out ${sid}__concatenated --config $params.config.utils.concatenate
        """
}
