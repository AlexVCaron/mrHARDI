#!/usr/bin/env nextflow

nextflow.enable.dsl=2


workflow print_channel {
    take:
        chan
        identifier
    main:
        chan.map { println "[DEBUG] $identifier : $it" }.view()
}