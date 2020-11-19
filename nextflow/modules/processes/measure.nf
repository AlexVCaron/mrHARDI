#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { get_size_in_gb; swap_configurations } from '../functions.nf'

params.config.measure.diamond = "$projectDir/.config/diamond_metrics.py"
params.config.measure.dti = "$projectDir/.config/dti_metrics.py"

process dti_metrics {
    memory { 2f * get_size_in_gb([mask] + (data instanceof List ? data : [data])) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/dti", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

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

process scil_dti_and_metrics {
    memory { 3f * get_size_in_gb([dwi, mask]) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$processing_caller_name/${task.process}_${task.index}", saveAs: { f -> f.contains("dti_dti") ? f : f.contains("metadata") ? f : null }, mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/all/${sid}/$measuring_caller_name/${task.process}_${task.index}",saveAs: { f -> f.contains("dti_dti") ? null : f.contains("metadata") ? null : f },  mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$processing_caller_name/dti", saveAs: { f -> f.contains("dti_dti") ? f : null }, mode: params.publish_mode
    publishDir "${params.output_root}/${sid}/$measuring_caller_name/dti", saveAs: { f -> f.contains("dti_dti") ? null : f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwi), path(bval), path(bvec), path(mask)
        val(processing_caller_name)
        val(measuring_caller_name)
    output:
        tuple val(sid), val("${sid}__dti"), emit: prefix
        tuple val(sid), path("${sid}__dti_dti.nii.gz"), emit: dti
        tuple val(sid), path("${sid}__dti_evals.nii.gz"), path("${sid}__dti_evecs.nii.gz"), path("${sid}__dti_evals_*.nii.gz"), path("${sid}__dti_evecs_*.nii.gz"), emit: eigen
        tuple val(sid), path("${sid}__dti_fa.nii.gz"), path("${sid}__dti_ga.nii.gz"), path("${sid}__dti_rgb.nii.gz"), emit: aniso
        tuple val(sid), path("${sid}__dti_md.nii.gz"), path("${sid}__dti_ad.nii.gz"), path("${sid}__dti_rd.nii.gz"), path("${sid}__dti_mode.nii.gz"), path("${sid}__dti_norm.nii.gz"), emit: iso
        tuple val(sid), path("${sid}__dti_non_physical.nii.gz"), path("${sid}__dti_pulsation*.nii.gz"), emit: artifacts, optional: true
        tuple val(sid), path("${sid}__dti_residuals.nii.gz"), path("${sid}__dti_residuals*.nii.gz"), emit: residuals, optional: true
    script:
        avail_threads = task.cpus / 3
        remainder_threads = task.cpus - avail_threads
        args = "--tensor ${sid}__dti_dti.nii.gz --evals ${sid}__dti_evals.nii.gz --evecs ${sid}__dti_evecs.nii.gz"
        args += " --fa ${sid}__dti_fa.nii.gz --ga ${sid}__dti_ga.nii.gz --rgb ${sid}__dti_rgb.nii.gz"
        args += " --md ${sid}__dti_md.nii.gz --ad ${sid}__dti_ad.nii.gz --rd ${sid}__dti_rd.nii.gz --mode ${sid}__dti_mode.nii.gz --norm ${sid}__dti_norm.nii.gz"
        if ( params.verbose_outputs )
            args += " --residual ${sid}__dti_residuals.nii.gz --non-physical ${sid}__dti_non_physical.nii.gz --pulsation ${sid}__dti_pulsation.nii.gz"

        """
        export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=${avail_threads + remainder_threads}
        export OMP_NUM_THREADS=$avail_threads
        export OPENBLAS_NUM_THREADS=1
        scil_compute_dti_metrics.py $dwi $bval $bvec --mask $mask -f $args
        """
}

process diamond_metrics {
    memory { 2.5 * get_size_in_gb(data + [mask]) }
    cpus 1
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/diamond", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

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
    memory { 2.5 * get_size_in_gb([odfs, fa, md, mask]) }
    label params.conservative_resources ? "res_conservative" : "res_full_node"
    errorStrategy "finish"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name/fodf", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(odfs), path(fa), path(md), file(mask)
        val(caller_name)
        val(basis)
    output:
        tuple val(sid), val("${sid}__fodf_metrics"), emit: prefix
        tuple val(sid), path("${sid}__fodf_metrics*.nii.gz"), emit: metrics
    script:
        """
        scil_compute_fodf_metrics.py --sh_basis $basis --mask $mask --afd_max ${sid}__fodf_metrics_afd.nii.gz --afd_total ${sid}__fodf_metrics_afdt.nii.gz --afd_sum ${sid}__fodf_metrics_afds.nii.gz --nufo ${sid}__fodf_metrics_nufo.nii.gz --peaks ${sid}__fodf_metrics_peaks.nii.gz --rgb ${sid}__fodf_metrics_rgb.nii.gz --peak_values ${sid}__fodf_metrics_peaks_values.nii.gz --peak_indices ${sid}__fodf_metrics_peaks_indices.nii.gz $odfs
        """
}

