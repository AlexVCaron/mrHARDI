#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.measure.diamond = "$projectDir/.config/diamond_metrics.py"
params.config.measure.dti = "$projectDir/.config/dti_metrics.py"

process dti_metrics {
    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), val(input_prefix), file(affine)
        val(caller_name)
    output:
        tuple val(sid), val("${sid}__dti_metrics")
    script:
        """
        magic-monkey dti_metrics --in $input_prefix --affine $affine --out ${sid}__dti_metrics --config $params.config.measure.dti
        """
}

process diamond_metrics {
    publishDir "${params.output_root}/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode

    input:
        tuple val(sid), val(input_prefix), file(affine)
        val(caller_name)
    output:
        tuple val(sid), val("${sid}__diamond_metrics")
    script:
        """
        magic-monkey diamond_metrics --in $input_prefix --affine $affine --out ${sid}__diamond_metrics --config $params.config.measure.diamond
        """
}
