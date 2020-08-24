#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.data_root = "data"
params.masked = true
params.masked_t1 = false
params.rev_is_b0 = true

include { key_from_filename } from "../modules/functions.nf"

workflow load_dataset {
    main:
        root = file(params.data_root)
        dwi_channel = Channel.fromFilePairs("$root/**/*dwi.{nii.gz,bvals,bvecs}", size: 3, flat: true).map{ [it[0], it[3], it[1], it[2]] }
        affine_channel = key_from_filename(Channel.fromPath("$root/**/*.affine"), ".")
        anat_channel = key_from_filename(Channel.fromPath("$root/**/*t1.nii.gz"), "_")

        if ( params.rev_is_b0 )
            rev_channel = key_from_filename(Channel.fromPath("$root/**/*rev.nii.gz"), "_")
        else
            rev_channel = Channel.fromFilePairs("$root/**/*rev.{nii.gz,bvals,bvecs}", size: 2, flat: true).map{ [it[0], it[3], it[1], it[2]] }

        if ( params.masked_t1 )
            anat_channel = anat_channel.join(key_from_filename(Channel.fromPath("$root/**/*mask.nii.gz"), "_"))
        else if ( params.masked )
            dwi_channel = dwi_channel.join(key_from_filename(Channel.fromPath("$root/**/*mask.nii.gz"), "_"))
    emit:
        dwi = dwi_channel
        affine = affine_channel
        anat = anat_channel
        rev = rev_channel
}
