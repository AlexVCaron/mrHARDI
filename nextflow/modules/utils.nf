#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.utils.apply_mask = "../.config/apply_mask.py"
params.config.utils.concatenate = "../.config/concatenate.py"

process apply_mask {
    input:
        tuple val(sid), path(img), path(mask)
    output:
        tuple val(sid), path("${sid}__masked.nii.gz")
    script:
        """
        magic_monkey apply_mask $img $mask ${sid}__masked.nii.gz --config $params.config.utils.apply_mask
        """
}

process bet_mask {
    input:
        tuple val(sid), path(img)
    output:
        tuple val(sid), path("${sid}__bet_mask.nii.gz")
    script:
        """
        magic_monkey bet $img ${sid}__bet_mask.nii.gz
        """
}

process cat_datasets {
    input:
        tuple val(sid), file(imgs)
    output:
        tuple val(sid), val("${sid}__concatenated")
    script:
        """
        magic_monkey concatenate $config --in imgs* --out ${sid}__concatenated --config $params.config.utils.concatenate
        """
}
