#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.masked_t1 = true
params.t1mask2dwi_registration = true
params.topup_correction = true
params.topup_mask = true
params.eddy_correction = true
params.gaussian_noise_correction = false
params.rician_noise_correction = true
params.rev_is_b0 = true
params.multiple_reps = false

params.config.workflow.preprocess.t12b0mask_registration = file("$projectDir/.config/.workflow/t12b0_mask_registration.py")
params.config.workflow.preprocess.topup_b0 = file("$projectDir/.config/.workflow/topup_b0.py")

include { group_subject_reps; join_optional; map_optional; opt_channel; replace_dwi_file; uniformize_naming; sort_as_with_name } from '../modules/functions.nf'
include { extract_b0 as dwi_b0; extract_b0 as b0_topup; squash_b0 as squash_dwi; squash_b0 as squash_rev } from '../modules/preprocess.nf'
include { n4_denoise; dwi_denoise; prepare_topup; topup; prepare_eddy; eddy } from '../modules/denoise.nf'
include { ants_register; ants_transform } from '../modules/register.nf'
include { cat_datasets as cat_topup; cat_datasets as cat_eddy; cat_datasets as cat_eddy_rev; cat_datasets as cat_eddy_on_rev; bet_mask; split_image; apply_topup; convert_datatype } from '../modules/utils.nf'


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

        squash_wkf( dwi_channel, rev_channel, meta_channel.join(rev_meta_channel) )

        if ( params.t1mask2dwi_registration || params.topup_correction ) {
            dwi_b0(dwi_channel.map{ it.subList(0, 3) }.join(meta_channel), "", "preprocess", "")
            b0_metadata = dwi_b0.out.metadata

            if ( params.t1mask2dwi_registration )
                mask_channel = t1_mask_to_dwi_wkf(dwi_b0.out.b0.groupTuple(), t1_channel.map{ [it[0], it[1]] }.groupTuple(), t1_channel.map{ [it[0], it[2]] }, b0_metadata.map{ it.subList(0, 2) + [""] }).image
            else if ( params.masked_t1 )
                mask_channel = t1_channel.map{ [it[0], it[2]] }

            if ( params.topup_correction ) {
                topup_wkf(squash_wkf.out.dwi, squash_wkf.out.rev, squash_wkf.out.metadata)

                topup2eddy_channel = topup_wkf.out.param.join(topup_wkf.out.prefix).join(topup_wkf.out.topup.map{ [it[0], it.subList(1, it.size())] })

                if ( !params.eddy_correction )
                    meta_channel = topup_wkf.out.metadata.map{ [it[0], it[2]] }
                else if ( params.eddy_pre_bet_mask ) {
                    mask_channel = bet_mask(topup_wkf.out.b0, "preprocess")
                }
            }
        }

        if ( params.eddy_correction ) {
            eddy_wkf(squash_wkf.out.dwi, mask_channel, topup2eddy_channel, squash_wkf.out.rev, squash_wkf.out.metadata)
            dwi_channel = replace_dwi_file(dwi_channel, eddy_wkf.out.dwi).map{ it.subList(0, 3) }.join(eddy_wkf.out.bvecs)
            meta_channel = eddy_wkf.out.metadata
        }
        else if ( params.topup_correction ) {
            dwi_channel = uniformize_naming(squash_wkf.out.dwi, "dwi_to_topup", "false")
            rev_channel = uniformize_naming(squash_wkf.out.rev, "dwi_to_topup_rev", "false")
            meta_channel = uniformize_naming(topup_wkf.out.in_metadata_w_topup.map{ [it[0], it[1][1]] }, "dwi_to_topup_metadata", "false")
            rev_meta_channel = uniformize_naming(topup_wkf.out.in_metadata_w_topup.map{ [it[0], it[1][0]] }, "dwi_to_topup_rev_metadata", "false")
            apply_topup_wkf(dwi_channel, rev_channel, topup2eddy_channel, meta_channel.join(rev_meta_channel).map{ [it[0], it.subList(1, it.size())] })
            dwi_channel = replace_dwi_file(dwi_channel, apply_topup_wkf.out.dwi)
            dwi_channel = uniformize_naming(dwi_channel, "topup_corrected", "false")
            meta_channel = uniformize_naming(apply_topup_wkf.out.metadata, "topup_corrected_metadata", "false")
        }

        if ( params.gaussian_noise_correction && !( ( params.eddy_correction && params.eddy_pre_denoise ) || params.rician_noise_correction ) ) {
            dwi_channel.view()
            meta_channel.view()
            mask_channel.view()
            dwi_denoise_wkf(dwi_channel.map{ it.subList(0, 2) }, mask_channel, meta_channel)
            dwi_channel = replace_dwi_file(dwi_channel, dwi_denoise_wkf.out.image)
            meta_channel = dwi_denoise_wkf.out.metadata
        }
        else if ( params.rician_noise_correction ) {
            n4_denoise_wkf(dwi_channel.map{ it.subList(0, 2) }, mask_channel, meta_channel)
            dwi_channel = replace_dwi_file(dwi_channel, n4_denoise_wkf.out.image)
            meta_channel = n4_denoise_wkf.out.metadata
        }

        dwi_channel = uniformize_naming(dwi_channel.map{ it.subList(0, 4) }, "dwi_preprocessed", "false")
        meta_channel = uniformize_naming(meta_channel, "dwi_preprocessed_metadata", "false")
        mask_channel = uniformize_naming(mask_channel, "mask_preprocessed", "false")
    emit:
        dwi = dwi_channel
        mask = mask_channel
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
        ants_register(t1_channel.join(b0_channel).join(b0_channel.map{ [it[0], it[1][0]] }).join(reg_metadata), "preprocess", params.config.workflow.preprocess.t12b0mask_registration)
        ants_reg = ants_register.out.affine.join(ants_register.out.syn, remainder: true).map{
            it[-1] ? it.subList(0, it.size() - 2) + [it[-1]] : it.subList(0, it.size() - 2) + [[]]
        }.map{
            it[-1].empty ? it : it.subList(0, it.size() - 1) + [it[-1].findAll{
                s -> !s.getName().contains("registration_inv_")
            }]
        }

        ants_transform(trans_channel.join(ants_register.out.reference).join(ants_reg).join(trans_metadata), "preprocess")
        convert_datatype(ants_transform.out.image, "int", "preprocess")
    emit:
        image = convert_datatype.out.image
}

// TODO : Here there is probably some metadatas from squashed process being tangled in i/o. The
// i/o bridge should be removed and the squashed metadatas should be passed directly to
// the delegated workflows/processes
workflow topup_wkf {
    take:
        dwi_channel
        rev_channel
        metadata_channel
    main:
        acq_channel = dwi_channel.map{ [it[0], it[2]] }.groupTuple().join(rev_channel.map{ [it[0], it[2]] }.groupTuple())
        meta_channel = metadata_channel.map{ it.subList(0, 2) }.groupTuple().join(
            metadata_channel.map{ [it[0], it[2]] }.groupTuple()
        ).map{ [it[0], it[1] + it[2]] }

        prepare_topup(acq_channel.join(meta_channel))

        data_channel = dwi_channel.map{ it.subList(0, 3) }.groupTuple().join(rev_channel.map{ it.subList(0, 3) }.groupTuple())

        cat_topup(data_channel.map { [it[0], it[1] + it[3], it[2] + it[4], []] }.join(meta_channel), "", "preprocess")
        b0_topup(cat_topup.out.image.join(cat_topup.out.bvals).join(cat_topup.out.metadata), "", "preprocess", params.config.workflow.preprocess.topup_b0)

        data_channel = prepare_topup.out.config.map{ it.subList(0, 4) }.join(b0_topup.out.b0)

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
        in_metadata_w_topup = sort_as_with_name(prepare_topup.out.in_metadata_w_topup, acq_channel.map{ it.flatten() })
}

workflow apply_topup_wkf {
    take:
        dwi_channel
        rev_channel
        topup_channel
        meta_channel
    main:
        data_channel = dwi_channel.map{ it.subList(0, 2) }.join(rev_channel.map{ it.subList(0, 2) })
        apply_topup(data_channel.join(topup_channel).join(meta_channel), "preprocess")
    emit:
        dwi = apply_topup.out.image
        metadata = apply_topup.out.metadata
}

// TODO : This workflow doesn't make sense, it is affected by decisions on eddy processing
// about what to do on rev squashing (should be imported to upper workflow)
workflow squash_wkf {
    take:
        dwi_channel
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
    emit:
        dwi = squash_dwi.out.dwi
        rev = rev_channel
        metadata = squash_dwi.out.metadata.join(rev_meta_channel)
}

workflow eddy_wkf {
    take:
        dwi_channel
        mask_channel
        topup_channel
        rev_channel
        metadata_channel
    main:

        bvals_channel = dwi_channel.map{ [it[0], "${it[2].getName()}".tokenize(".")[0]] }
        bvals_channel = join_optional(bvals_channel, topup_channel.map{ [it[0], it[1]] })
        bvals_channel = join_optional(bvals_channel, rev_channel.map{ [it[0], "${it[2].getName()}".tokenize(".")[0]] })

        metadata_channel = metadata_channel.map{ [it[0], it.subList(1, it.size())] }

        prepare_eddy(bvals_channel.join(dwi_channel.join(rev_channel).map{ [it[0], it.subList(1, it.size())] }).join(metadata_channel))

        if ( params.eddy_on_rev ) {
            cat_eddy_on_rev(dwi_channel.concat(rev_channel).groupTuple().join(metadata_channel), "_whole", "preprocess")
            dwi_channel = cat_eddy_on_rev.out.image.join( cat_eddy_on_rev.out.bvals).join(cat_eddy_on_rev.out.bvecs)
            metadata_channel = cat_eddy_on_rev.out.metadata.map{ [it[0], it.subList(1, it.size())] }
        }

        if ( params.eddy_pre_denoise ) {
            dwi_denoise_wkf(dwi_channel.map{ it.subList(0, 2) }, null, metadata_channel)
            dwi_channel = replace_dwi_file(dwi_channel, dwi_denoise_wkf.out.image)
            metadata_channel = dwi_denoise_wkf.out.metadata.map{ [it[0], it.subList(1, it.size())] }
        }

        dwi_channel = join_optional(dwi_channel, mask_channel)
        dwi_channel = join_optional(dwi_channel, topup_channel.map{ [it[0], it[2], it[3]] })

        eddy_in = prepare_eddy.out.config
        if ( params.use_cuda )
            eddy_in = eddy_in.join(prepare_eddy.out.slspec)
        else
            eddy_in = eddy_in.map{ it + [""] }

        dwi_channel = eddy_in.join(dwi_channel).join(metadata_channel)
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

workflow n4_denoise_wkf {
    take:
        dwi_channel
        mask_channel
        metadata_channel
    main:
        dwi_channel = join_optional(dwi_channel, mask_channel)
        n4_denoise(dwi_channel.join(metadata_channel), "preprocess")
    emit:
        image = n4_denoise.out.image
        metadata = n4_denoise.out.metadata
}
