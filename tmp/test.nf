#!/usr/bin/env nextflow

nextflow.enable.dsl=2

process test_proc {
    input:
        tuple val(sid), file(data)
    output:
        tuple val(sid), file("${sid}__test_out")
    script:
        """
        touch ${sid}__test_out
        """
}

workflow test_workflow {
    take: in_channel
    main:
        test_proc(in_channel)
    emit:
        out_file = test_proc.out
}

input_channel = Channel.from([sid: 1, data: "file_1"])

workflow {
    test_workflow(input_channel) | view
}
