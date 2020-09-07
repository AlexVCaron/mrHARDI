#!/usr/bin/env nextflow

nextflow.enable.dsl=2

def key_from_filename ( chan, split_char ) {
    return chan.map{ [ it.getFileName().toString().substring(0, it.getFileName().toString().lastIndexOf(split_char)), it ] }
}

def group_subject_reps ( dwi_channel ) {
    return dwi_channel.groupTuple().map{
        [it[0]] + it.subList(1, it.size()).inject((1..it.size()).collect{ [] }) { sub, rep ->
            sub.eachWithIndex { its, i -> its.add(rep[i]) } ; return sub
        }
    }
}

def replace_dwi_file ( base_channel, dwi_channel ) {
    return dwi_channel.join(base_channel.map{ [it[0]] + it.subList(2, it.size()) })
}

OPT_FILE_VALUE = ""
OPT_CHANNEL = null

def opt_channel () {
    return OPT_CHANNEL
}

def join_optional ( base_channel, opt_channel ) {
    if ( opt_channel )
        return base_channel.join(opt_channel)
    else
        return base_channel.map{ it + [OPT_FILE_VALUE] }
}

def map_optional ( base_channel, opt_idx ) {
    return base_channel.map{ [it[0], it[opt_idx]] }.map{ it[1] ? it : [it[0], OPT_FILE_VALUE] }
}