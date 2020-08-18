#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.data_root = "data"
params.masked = true
params.masked_t1 = false

workflow load_dataset {
    main:
        root = path(params.data_root)
        dwi_channel = Channel.fromFilePairs("$root/**/*{dwi.nii.gz,bvals,bvecs}")
        affine_channel = Channel.fromFilePairs("$root/**/*{affine}")
        rev_channel = Channel.fromFilePairs("$root/**/*{rev.nii.gz}")
        anat_channel = Channel.fromFilePairs("$root/**/*{t1.nii.gz}")
        if ( params.masked_t1 )
            anat_channel.join(Channel.fromFilePairs("$root/**/*{mask.nii.gz}"))
        else if ( params.masked )
            dwi_channel.join(Channel.fromFilePairs("$root/**/*{mask.nii.gz}"))
    emit:
        dwi = dwi_channel
        affine = affine_channel
        anat = anat_channel
        rev = rev_channel
}
