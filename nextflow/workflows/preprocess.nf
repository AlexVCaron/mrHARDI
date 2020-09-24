#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.masked_t1 = true
params.t1mask2dwi_registration = true
params.topup_correction = true
params.topup_mask = true
params.eddy_correction = true
params.gaussian_noise_correction = true
params.rev_is_b0 = true
params.multiple_reps = false

params.config.workflow.preprocess.t12b0mask_registration = "$projectDir/.config/.workflow/t12b0_mask_registration.py"

include { group_subject_reps; join_optional; map_optional; opt_channel; replace_dwi_file } from '../modules/functions.nf'
include { extract_b0 as dwi_b0; extract_b0 as b0_rev; squash_b0 as squash_dwi; squash_b0 as squash_rev } from '../modules/preprocess.nf'
include { dwi_denoise; prepare_topup; topup; prepare_eddy; eddy; apply_topup } from '../modules/denoise.nf'
include { ants_register; ants_transform } from '../modules/register.nf'
include { cat_datasets as cat_topup; cat_datasets as cat_eddy; cat_datasets as cat_eddy_rev; cat_datasets as cat_eddy_on_rev } from '../modules/utils.nf'


workflow preprocess_wkf {
    take:
        dwi_channel
        rev_channel
        t1_channel
        meta_channel
        rev_meta_channel
    main:
        mask_channel = map_optional(dwi_channel, 4)
        dwi_channel = dwi_channel.map{ it.subList(0, 4) }
        topup2eddy_channel = opt_channel()

        if ( params.t1mask2dwi_registration || params.topup_correction ) {
            dwi_b0(dwi_channel.map{ it.subList(0, 3) }.join(meta_channel), "", "preprocess")
            b0_metadata = dwi_b0.out.metadata

            if ( params.rev_is_b0 )
                rev_b0_channel = rev_channel.join(rev_meta_channel, remainder: true).map{ it.size() == 2 ? it + [""] : it.size() == 4 ? it + [""] : it }
            else {
                in_rev = rev_channel.map{ it.subList(0, 3) }.join(rev_meta_channel)
                b0_rev(in_rev, "_rev", "preprocess")
                rev_b0_channel = b0_rev.out.b0
                b0_metadata = b0_metadata.join(b0_rev.out.metadata)
            }

            // TODO : Check registration when singularity is up
            if ( params.t1mask2dwi_registration )
                mask_channel = t1_mask_to_dwi_wkf(dwi_b0.out.b0, t1_channel.map{ [it[0], it[1]] }, t1_channel.map{ [it[0], it[2]] }, b0_metadata.map{ it.subList(0, 2) + [""] }).image
            else if ( params.masked_t1 )
                mask_channel = t1_channel.map{ [it[0], it[2]] }

            if ( params.topup_correction ) {
                topup_wkf(dwi_b0.out.b0, rev_b0_channel, b0_metadata)
                // TODO : Implement topup mask computation
                topup2eddy_channel = topup_wkf.out.param.join(topup_wkf.out.prefix).join(topup_wkf.out.topup.map{ [it[0], it.subList(1, it.size())] })
                if ( !params.eddy_correction )
                    meta_channel = topup_wkf.out.metadata
            }
        }

        if ( params.eddy_correction ) {
            eddy_wkf(dwi_channel, mask_channel, topup2eddy_channel, rev_channel, meta_channel.join(rev_meta_channel))
            dwi_channel = replace_dwi_file(dwi_channel, eddy_wkf.out.dwi).map{ it.subList(0, 3) }.join(eddy_wkf.out.bvecs).join(mask_channel)
            meta_channel = eddy_wkf.out.metadata
        }
        else if ( params.topup_correction ) {
            apply_topup_wkf(dwi_channel, topup_channel)
            dwi_channel = replace_dwi_file(dwi_channel, apply_topup_wkf.out.image)
            meta_channel = apply_topup_wkf.out.metadata
        }

        if ( params.gaussian_noise_correction ) {
            dwi_denoise_wkf(dwi_channel, mask_channel, meta_channel)
            dwi_channel = replace_dwi_file(dwi_channel, dwi_denoise_wkf.out.image)
            meta_channel = dwi_denoise_wkf.out.metadata
        }

    emit:
        dwi = dwi_channel
        metadata = meta_channel
}

workflow t1_mask_to_dwi_wkf {
    take:
        b0_channel
        t1_channel
        trans_channel
        metadata_channel
    main:
        reg_metadata = metadata_channel.map{ it.subList(0, it.size() - 1)}
        trans_metadata =  metadata_channel.map{ [it[0], it[-1]] }

        ants_register(t1_channel.join(b0_channel).join(reg_metadata), "preprocess", params.config.workflow.preprocess.t12b0mask_registration)
        ants_reg = ants_register.out.affine.join(ants_register.out.syn, remainder: true).map{
            it[-1] ? it: it.subList(0, it.size() - 1) + [[]]
        }.map{
            it[-1].empty ? it : it.subList(0, it.size() - 1) + [it[-1].findAll{
                s -> !s.getName().contains("registration_inv_")
            }]
        }

        ants_transform(trans_channel.join(ants_reg).join(trans_metadata), "preprocess")
    emit:
        image = ants_transform.out.image
        metadata = ants_transform.out.metadata
}

workflow topup_wkf {
    take:
        b0_channel
        rev_b0_channel
        metadata_channel
    main:
        data_channel = b0_channel.groupTuple().join(rev_b0_channel.groupTuple())
        meta_channel = metadata_channel.map{ it.subList(0, 2) }.groupTuple().join(metadata_channel.map{ [it[0], it[2]] }.groupTuple()).map{ [it[0], it[1] + it[2]] }

        prepare_topup(data_channel.join(meta_channel))
        cat_topup(data_channel.map { [it[0], it[1] + it[2], [], []] }.join(meta_channel), "", "preprocess")

        data_channel = prepare_topup.out.config.map{ it.subList(0, 4) }.join(cat_topup.out.image)

        topup(data_channel.join(prepare_topup.out.metadata), "preprocess")
    emit:
        b0 = topup.out.image
        field = topup.out.field
        movpar = topup.out.transfo.map{ [it[0], it[1]] }
        coeff = topup.out.transfo.map{ [it[0], it[2]] }
        param = prepare_topup.out.config.map{ [it[0], it[2]] }
        prefix = prepare_topup.out.config.map{ [it[0], it[-1]] }
        topup = topup.out.pkg
        metadata = prepare_topup.out.metadata
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
        metadata_channel
    main:
        dwi_meta_channel = metadata_channel.map{ it.subList(0, 2) }
        rev_meta_channel = metadata_channel.map{ [it[0], it[2]] }

        if ( params.multiple_reps ) {
            grouped_dwi = group_subject_reps(dwi_channel, dwi_meta_channel)
            cat_eddy(grouped_dwi[0].join(grouped_dwi[1]), "", "preprocess")
            dwi_channel = cat_eddy.out.image
            dwi_meta_channel = cat_eddy.out.metadata

            if ( rev_channel ) {
                grouped_dwi = group_subject_reps(dwi_channel, dwi_meta_channel)
                cat_eddy_rev(grouped_dwi[0].join(grouped_dwi[1]), "_rev", "preprocess")
                rev_channel = cat_eddy_rev.out.image
                rev_meta_channel = cat_eddy_rev.out.metadata
            }
        }

        squash_dwi(dwi_channel.join(dwi_meta_channel), "", "preprocess")
        if ( params.eddy_on_rev ) {
            squash_rev(rev_channel.join(rev_meta_channel), "_rev", "preprocess")
            rev_channel = squash_rev.out.dwi
            rev_meta_channel = squash_rev.out.metadata
        }

        bvals_channel = squash_dwi.out.dwi.map{ [it[0], it[2]] }
        bvals_channel = join_optional(bvals_channel, topup_channel.map{ [it[0], it[1]] })
        bvals_channel = join_optional(bvals_channel, rev_channel.map{ [it[0], it[2]] })

        meta_channel = squash_dwi.out.metadata.join(rev_meta_channel).map{ [it[0], [it[1], it[2]]] }
        prepare_eddy(bvals_channel.join(meta_channel))

        dwi_channel = squash_dwi.out.dwi
        if ( params.eddy_on_rev ) {
            cat_eddy_on_rev(squash_dwi.out.dwi.concat(rev_channel).groupTuple().join(meta_channel), "_whole", "preprocess")
            dwi_channel = cat_eddy_on_rev.out.image.map{ [it[0]] + it[1].sort{ f -> [ "nii.gz", "bvals", "bvecs" ].indexOf("$f".tokenize('.').subList(1, "$f".tokenize('.').size()).join('.')) } }
            meta_channel = cat_eddy_on_rev.out.metadata
        }

        dwi_channel = join_optional(dwi_channel, mask_channel)
        dwi_channel = join_optional(dwi_channel, topup_channel.map{ [it[0], it[2], it[3]] })
        dwi_channel = prepare_eddy.out.config.join(dwi_channel).join(meta_channel)
        dwi_channel.view()
        eddy(dwi_channel, "preprocess")
    emit:
        dwi = eddy.out.dwi
        bvecs = eddy.out.bvecs
        metadata = eddy.out.metadata
}

workflow dwi_denoise_wkf {
    take:
        dwi_channel
        mask_channel
        metadata_channel
    main:
        dwi_channel = join_optional(dwi_channel, mask_channel)
        dwi_denoise(dwi_channel.join(metadata_channel), "preprocess")
    emit:
        image = dwi_denoise.out.image
        metadata = dwi_denoise.out.metadata
}
