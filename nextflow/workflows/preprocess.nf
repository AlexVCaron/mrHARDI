#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.t1mask2dwi_registration = true
params.topup_correction = true
params.topup_mask = true
params.eddy_correction = true
params.gaussian_noise_correction = true
params.rev_is_b0 = true
params.multiple_reps = false

include { group_subject_reps; join_optional; map_optional; opt_channel; replace_dwi_file } from '../modules/functions.nf'
include { extract_b0 as b0; extract_b0 as b0_rev; squash_b0 } from '../modules/preprocess.nf'
include { dwi_denoise; prepare_topup; topup; prepare_eddy; eddy; apply_topup } from '../modules/denoise.nf'
include { ants_register; ants_transform } from '../modules/register.nf'
include { cat_datasets as cat_topup; cat_datasets as cat_eddy } from '../modules/utils.nf'

workflow preprocess_wkf {
    take:
        dwi_channel
        rev_channel
        t1_channel
    main:
        mask_channel = map_optional(dwi_channel, 4)
        dwi_channel = dwi_channel.map{ it.subList(0, 4) }
        topup2eddy_channel = opt_channel()

        if ( params.t1mask2dwi_registration || params.topup_correction ) {
            b0_channel = b0(dwi_channel.map{ it.subList(0, 3) })
            rev_b0_channel = rev_channel

            if ( ! params.rev_is_b0 )
                rev_b0_channel = b0_rev(rev_channel)

// TODO : Check registration when singularity is up
            if ( params.t1mask2dwi_registration )
                mask_channel = t1_mask_to_dwi_wkf(b0_channel, t1_channel.map{ [it[0], it[1]] }, t1_channel.map{ [it[0], it[2]] })

            if ( params.topup_correction ) {
                topup_wkf(b0_channel, rev_b0_channel, mask_channel)
// TODO : Implement topup mask computation
                topup2eddy_channel = topup_wkf.out.param
            }
        }

        if ( params.eddy_correction ) {
            eddy_wkf(dwi_channel, mask_channel, topup2eddy_channel, rev_channel)
            dwi_channel = replace_dwi_file(dwi_channel, eddy_wkf.out.dwi).map{ it.subList(0, 3) }.join(eddy_wkf.out.bvecs).join(mask_channel)
        }
        else if ( params.topup_correction )
            dwi_channel = replace_dwi_file(dwi_channel, apply_topup_wkf(dwi_channel, topup_channel))

        if ( params.gaussian_noise_correction )
            dwi_channel = replace_dwi_file(dwi_channel, dwi_denoise_wkf(dwi_channel))

    emit:
        dwi_channel
}

workflow t1_mask_to_dwi_wkf {
    take:
        b0_channel
        t1_channel
        trans_channel
    main:
        ants_register(t1_channel.join(b0_channel))
        ants_transform(trans_channel.join(ants_register.out))
    emit:
        ants_transform.out
}

workflow topup_wkf {
    take:
        b0_channel
        rev_b0_channel
        mask_channel
    main:
        data_channel = b0_channel.groupTuple().join(rev_b0_channel.groupTuple())
        prep_channel = prepare_topup(data_channel)
        cat_channel = cat_topup(data_channel.map { [it[0], it[1] + it[2], "", ""] })

        data_channel = prep_channel.map{ it.subList(0, 3) }.join(cat_channel)
        data_channel = join_optional(data_channel, mask_channel)

        topup(data_channel)
    emit:
        b0 = topup.out.map{ [it[0], it[1]] }
        field = topup.out.map{ [it[0], it[2]] }
        movpar = topup.out.map{ [it[0], it[3]] }
        coeff = topup.out.map{ [it[0], it[4]] }
        param = prepare_topup.out.map{ [it[0], it[2]] }
        prefix = prepare_topup.out.map{ [it[0], it[-1]] }
}

//workflow apply_topup_wkf {
//    take:
//        dwi_channel
//        topup_channel
//    main:
//        apply_topup
//}

workflow eddy_wkf {
    take:
        dwi_channel
        mask_channel
        topup_channel
        rev_channel
    main:
        if ( params.multiple_reps ) {
            grouped_channel = group_subject_reps(dwi_channel)
            dwi_channel = cat_eddy(grouped_channel)
        }

        bvals_channel = squash_b0(dwi_channel).map{ [it[0], it[2]] }
        bvals_channel = join_optional(bvals_channel, topup_channel)
        bvals_channel = join_optional(bvals_channel, rev_channel.map{ [it[0], it[2]] })

        prepare_eddy(bvals_channel)

        dwi_channel = join_optional(dwi_channel, mask_channel)
        eddy(prepare_eddy.out.join(dwi_channel))

    emit:
        dwi = eddy.out.map{ [it[0], it[1]] }
        bvecs = eddy.out.map{ [it[0], it[2]] }
}

workflow dwi_denoise_wkf {
    take: dwi_channel
    main:
        dwi_denoise(dwi_channel)
    emit:
        dwi_denoise.out
}
