#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.measure.diamond = "../.config/diamond_mtr.py"
params.config.measure.dti = "../.config/dti_mtr.py"

process dti_metrics {
    input:
        tuple val(sid), val(input_prefix), file(affine)
    output:
        tuple val(sid), val("${sid}__dti_metrics")
    script:
        """
        magic_monkey dti_metrics --in $input_prefix --affine $affine --out ${sid}__dti_metrics --config $params.config.measure.dti
        """
}

process diamond_metrics {
    input:
        tuple val(sid), val(input_prefix), file(affine)
    output:
        tuple val(sid), val("${sid}__diamond_metrics")
    script:
        """
        magic_monkey diamond_metrics --in $input_prefix --affine $affine --out ${sid}__diamond_metrics --config $params.config.measure.diamond
        """
}
