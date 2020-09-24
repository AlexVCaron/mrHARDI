#!/usr/bin/env nextflow

nextflow.enable.dsl=2


params.metadata.acquisition = "Linear"
params.metadata.direction = "AP"
params.metadata.dwell = 0.112
params.metadata.multiband = 1
params.metadata.interleaved = false

def metadata_from_params ( reverse ) {
    direction = reverse ? "${params.metadata.direction}".reverse() : "${params.metadata.direction}"
    return "--acq ${params.metadata.acquisition} --dir $direction --dwell ${params.metadata.dwell} --mb ${params.metadata.multiband}"
}

process prepare_metadata {
    input:
        tuple val(sid), path(image), file(metadata)
        val(reverse)
    output:
        tuple val(sid), path("${sid}*_metadata.py")
    script:
        args = ""
        if ( !metadata.empty() )
            args += "--json $metadata"
        else
            args += metadata_from_params(reverse)
        """
        magic-monkey metadata --in $image $args
        """
}
