#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { get_size_in_gb; prevent_sci_notation; swap_configurations } from './functions.nf'

params.config.measure.diamond = "$projectDir/.config/diamond_metrics.py"
params.config.measure.dti = "$projectDir/.config/dti_metrics.py"

process dti_metrics {
    memory { "${prevent_sci_notation(get_size_in_gb(data[0]))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript { "cp $params.config.measure.dti config.py" }
    input:
        tuple val(sid), val(input_prefix), file(mask), path(data), path(metadata)
        val(caller_name)
        file(config_overwrite)
    output:
        tuple val(sid), val("${sid}__dti_metrics"), emit: prefix
        tuple val(sid), path("${sid}__dti_metrics*.nii.gz"), emit: metrics
    script:
        config = swap_configurations("config.py", config_overwrite)
        """
        magic-monkey dti_metrics --in $input_prefix --out ${sid}__dti_metrics --config $config
        """
}

process diamond_metrics {
    memory { "${prevent_sci_notation(get_size_in_gb(data[0]))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), val(input_prefix), file(mask), path(data), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), val("${sid}__diamond_metrics"), emit: prefix
        tuple val(sid), path("${sid}__diamond_metrics*.nii.gz"), emit: metrics
    script:
        """
        magic-monkey diamond_metrics --in $input_prefix --out ${sid}__diamond_metrics --config $params.config.measure.diamond
        """
}

process odf_metrics {
    memory { "${prevent_sci_notation(get_size_in_gb(odfs))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(odfs), path(fa), path(md), file(mask)
        val(caller_name)
    output:
        tuple val(sid), val("${sid}__fodf_metrics"), emit: prefix
        tuple val(sid), path("${sid}__fodf_metrics*.nii.gz"), emit: metrics
    script:
        """
        scil_compute_fodf_metrics.py --sh_basis tournier07 --mask $mask --afd_max ${sid}__fodf_metrics_afd.nii.gz --afd_total ${sid}__fodf_metrics_afdt.nii.gz --afd_sum ${sid}__fodf_metrics_afds.nii.gz --nufo ${sid}__fodf_metrics_nufo.nii.gz --peaks ${sid}__fodf_metrics_peaks.nii.gz --rgb ${sid}__fodf_metrics_rgb.nii.gz --peak_values ${sid}__fodf_metrics_peaks_values.nii.gz --peak_indices ${sid}__fodf_metrics_peaks_indices.nii.gz $odfs
        """
}