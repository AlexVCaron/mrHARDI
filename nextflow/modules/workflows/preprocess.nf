#!/usr/bin/env nextflow

nextflow.enable.dsl=2

params.masked_t1 = true
params.t1mask2dwi_registration = true
params.topup_correction = true
params.topup_mask = true
params.eddy_correction = true
params.post_eddy_registration = true
params.gaussian_noise_correction = true
params.intensity_normalization = true
params.rev_is_b0 = true
params.multiple_reps = false

params.config.workflow.preprocess.t12b0mask_registration = file("$projectDir/.config/.workflow/t12b0_mask_registration.py")
params.config.workflow.preprocess.post_eddy_registration = file("$projectDir/.config/.workflow/post_eddy_ants_registration.py")
params.config.workflow.preprocess.topup_b0 = file("$projectDir/.config/.workflow/topup_b0.py")

include { group_subject_reps; join_optional; map_optional; opt_channel; replace_dwi_file; uniformize_naming; sort_as_with_name } from '../functions.nf'
include { extract_b0 as dwi_b0; extract_b0 as b0_topup; extract_b0 as b0_topup_rev; squash_b0 as squash_dwi; squash_b0 as squash_rev } from '../processes/preprocess.nf'
include { n4_denoise; dwi_denoise; prepare_topup; topup; prepare_eddy; eddy } from '../processes/denoise.nf'
include { ants_register; ants_transform } from '../processes/register.nf'
include { cat_datasets as cat_topup; cat_datasets as cat_eddy; cat_datasets as cat_eddy_rev; cat_datasets as cat_eddy_on_rev; bet_mask; split_image; apply_topup; convert_datatype; replicate_image; check_dwi_conformity } from '../processes/utils.nf'

workflow registration_wkf {
    take:
        target_channel
        moving_channel
        trans_channel
        metadata_channel
        parameters
    main:
        reg_metadata = metadata_channel.map{ it.subList(0, it.size() - 1)}
        trans_metadata =  metadata_channel.map{ [it[0], it[-1]] }
        ants_register(moving_channel.join(target_channel).join(target_channel.map{ [it[0], it[1][0]] }).join(reg_metadata), "preprocess", parameters)
        ants_reg = ants_register.out.affine.join(ants_register.out.syn, remainder: true).map{
            it[-1] ? it.subList(0, it.size() - 2) + [it[-1]] : it.subList(0, it.size() - 2) + [[]]
        }.map{
            it[-1].empty ? it : it.subList(0, it.size() - 1) + [it[-1].findAll{
                s -> !s.getName().contains("registration_inv_")
            }]
        }

        if ( trans_channel ) {
            ants_transform(trans_channel.join(ants_register.out.reference).join(ants_reg).join(trans_metadata), "preprocess")
            img = ants_transform.out.image
        }
        else {
            img = ants_register.out.image
        }
    emit:
        image = img
        registration = ants_register.out.image
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

        b0_topup(dwi_channel.map{ it.subList(0, 3) }.join(meta_channel), "", "preprocess", params.config.workflow.preprocess.topup_b0)
        b0_topup_rev(rev_channel.map{ it.subList(0, 3) }.join(meta_channel), "_rev", "preprocess", params.config.workflow.preprocess.topup_b0)

        data_channel = b0_topup.out.b0.groupTuple().join(b0_topup_rev.out.b0.groupTuple())

        cat_topup(data_channel.map { [it[0], it[1] + it[2], [], []] }.join(b0_topup.out.metadata.join(b0_topup_rev.out.metadata).map{ [it[0], it.subList(1, it.size())] }), "", "preprocess")

        metadata_channel = cat_topup.out.metadata.join(meta_channel).map{ [it[0], [it[1]] + it[2]] }

        prepare_topup(cat_topup.out.image.join(dwi_channel.map{ [it[0], it[2]] }).join(rev_channel.map{ [it[0], it[2]] }).join(metadata_channel))

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
        topup_b0_channel
        rev_channel
        metadata_channel
    main:

        bval_channel = dwi_channel.map{ [it[0], "${it[2].getName()}".tokenize(".")[0]] }
        bval_channel = join_optional(bval_channel, topup_channel.map{ [it[0], it[1]] })
        bval_channel = join_optional(bval_channel, rev_channel.map{ [it[0], "${it[2].getName()}".tokenize(".")[0]] })

        metadata_channel = metadata_channel.map{ [it[0], it.subList(1, it.size())] }

        prepare_eddy(bval_channel.join(dwi_channel.join(rev_channel).map{ [it[0], it.subList(1, it.size())] }).join(metadata_channel))

        dwi_channel = dwi_channel.map{ it.subList(0, 3)}.join(prepare_eddy.out.bvec.map{ [it[0], it[1].find{ f -> f.simpleName.indexOf("_rev") == -1 }] })
        rev_channel = rev_channel.map{ it.subList(0, 3)}.join(prepare_eddy.out.bvec.map{ [it[0], it[1].find{ f -> f.simpleName.indexOf("_rev") >= 0 }] })

        if ( params.eddy_on_rev ) {
            cat_eddy_on_rev(dwi_channel.concat(rev_channel).groupTuple().join(metadata_channel), "_whole", "preprocess")
            dwi_channel = cat_eddy_on_rev.out.image.join( cat_eddy_on_rev.out.bval).join(cat_eddy_on_rev.out.bvec)
            metadata_channel = cat_eddy_on_rev.out.metadata.map{ [it[0], it.subList(1, it.size())] }
        }

        // if ( params.eddy_pre_denoise ) {
        //    dwi_denoise_wkf(dwi_channel.map{ it.subList(0, 2) }, null, metadata_channel)
        //    dwi_channel = replace_dwi_file(dwi_channel, dwi_denoise_wkf.out.image)
        //    metadata_channel = dwi_denoise_wkf.out.metadata.map{ [it[0], it.subList(1, it.size())] }
        // }

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
        check_dwi_conformity(eddy.out.dwi.join(eddy.out.bval).join(eddy.out.bvec).join(eddy.out.metadata), "fix")
    emit:
        dwi = check_dwi_conformity.out.dwi.map{ [it[0], it[1]] }
        bval = check_dwi_conformity.out.dwi.map{ [it[0], it[2]] }
        bvec = check_dwi_conformity.out.dwi.map{ [it[0], it[3]] }
        metadata = check_dwi_conformity.out.metadata
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
        b0_channel
        mask_channel
        metadata_channel
        config_override
    main:
        dwi_channel = join_optional(dwi_channel, b0_channel)
        dwi_channel = join_optional(dwi_channel, mask_channel)
        dwi_channel = join_optional(dwi_channel, metadata_channel)
        n4_denoise(dwi_channel, "preprocess", config_override)
    emit:
        image = n4_denoise.out.image
        metadata = n4_denoise.out.metadata
}