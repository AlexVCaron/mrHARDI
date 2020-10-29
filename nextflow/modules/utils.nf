#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.config.utils.apply_mask = "$projectDir/.config/apply_mask.py"
params.config.utils.concatenate = "$projectDir/.config/cat.py"

include { get_size_in_gb; prevent_sci_notation } from './functions.nf'

process apply_mask {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(img))} GB" }

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.utils.apply_mask config.py"
    input:
        tuple val(sid), path(img), path(mask), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__masked.nii.gz"), emit: image
        tuple val(sid), path("${sid}__masked_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey apply_mask $img $mask ${sid}__masked.nii.gz --config config.py
        """
}

process bet_mask {
    memory { "${prevent_sci_notation(get_size_in_gb(img))} GB" }

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(img)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__bet_mask.nii.gz")
    script:
        """
        fslmaths $img -Tmean $img
        bet $img "${sid}__bet.nii.gz" -m -R -f $params.bet.f
        """
}

process cat_datasets {
    memory { "${prevent_sci_notation(2f * get_size_in_gb(imgs))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    beforeScript "cp $params.config.utils.concatenate config.py"
    input:
        tuple val(sid), file(imgs), file(bvals), file(bvecs), file(metadatas)
        val(suffix)
        val(caller_name)
    output:
        tuple val(sid), file("${sid}__concatenated${suffix}.nii.gz"), emit: image
        tuple val(sid), file("${sid}__concatenated${suffix}.bvals"), optional: true, emit: bvals
        tuple val(sid), file("${sid}__concatenated${suffix}.bvecs"), optional: true, emit: bvecs
        tuple val(sid), file("${sid}__concatenated${suffix}_metadata.*"), optional: true, emit: metadata
    script:
        args = "--in ${imgs.join(',')}"

        if ( bvals.size() > 0 )
            args += " --bvals ${bvals.join(',')}"
        if ( bvecs.size() > 0 )
            args += " --bvecs ${bvecs.join(',')}"

        """
        magic-monkey concatenate $args --out ${sid}__concatenated${suffix} --config config.py
        """
}

process split_image {
    memory { "${prevent_sci_notation(get_size_in_gb(img))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(img), path(metadata)
        val(split_axis)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__splitted_ax${split_axis}_[0-9]*.nii.gz"), emit: images
        tuple val(sid), path("${sid}__splitted_ax${split_axis}_*_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey split --image $img --prefix "${sid}__splitted" --axis $split_axis
        """
}

process join_images {
    memory { "${prevent_sci_notation(get_size_in_gb(imgs))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), val(prefix), path(imgs), path(metadatas)
        val(split_axis)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__joined_ax${split_axis}.nii.gz"), emit: image
        tuple val(sid), file("${sid}__joined_ax${split_axis}_*_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey split --image ${sid}__joined_ax${split_axis}.nii.gz --prefix $prefix --axis $split_axis --inverse
        """
}

process apply_topup {
    memory { "${prevent_sci_notation(get_size_in_gb(dwis))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(dwis), path(revs), path(topup_params), val(topup_prefix), path(topup_files), path(metadata)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__topup_corrected.nii.gz"), emit: image
        tuple val(sid), file("${sid}__topup_corrected_metadata.*"), optional: true, emit: metadata
    script:
        """
        magic-monkey apply_topup --dwi ${dwis.join(",")} --rev ${revs.join(",")}  --acqp $topup_params --topup $topup_prefix --out ${sid}__topup_corrected
        """
}

process tournier2descoteaux_odf {
    memory { "${prevent_sci_notation(get_size_in_gb(odfs))} GB" }
    label "res_full_node"

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(odfs)
        val(caller_name)
    output:
        tuple val(sid), path("${sid}__desc07_odf.nii.gz"), emit: odfs
    script:
        """
        scil_convert_sh_basis.py $odfs ${sid}__desc07_odf.nii.gz tournier07
        """
}

process convert_datatype {
    memory { "${prevent_sci_notation(get_size_in_gb(image))} GB" }
    cpus 1

    publishDir "${params.output_root}/all/${sid}/$caller_name/${task.process}_${task.index}", mode: params.publish_mode, enabled: params.publish_all
    publishDir "${params.output_root}/${sid}/$caller_name", saveAs: { f -> f.contains("metadata") ? null : f }, mode: params.publish_mode

    input:
        tuple val(sid), path(image)
        val(datatype)
        val(caller_name)
    output:
        tuple val(sid), path("${image.simpleName}_dt_${datatype}.nii.gz"), emit: image
    script:
        """
        magic-monkey convert --in $image --out "${image.simpleName}_dt_${datatype}.nii.gz" --dt $datatype
        """
}