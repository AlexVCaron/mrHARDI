from enum import Enum

import piper.comm as comm
import piper.graph.models
import piper.pipeline as pipeline


class ModelTraits(Enum):
    CHANNEL = (piper.graph.models.Channel, comm.Channel)
    SUBSCRIBER = (piper.graph.models.Subscriber, comm.subscriber)
    PROCESS = (piper.graph.models.Process, pipeline.Process)
    UNIT = (piper.graph.models.Unit, pipeline.Unit)
    LAYER = (piper.graph.models.Layer, pipeline.Layer)
    PIPELINE = (piper.graph.models.Pipeline, pipeline.Pipeline)


def get_all_parents(obj_klass):
    parents = obj_klass.__bases__
    if len(parents) > 0 and parents[0] is not object:
        return parents + tuple(
            pp for p in parents for pp in get_all_parents(p)
        )

    return tuple()


def get_associated_model(obj_klass):
    related_traits = list(filter(
        lambda trait: trait.value[1] in get_all_parents(obj_klass),
        list(ModelTraits)
    ))
    p_len = len(related_traits) + 1
    while len(related_traits) > 1 and not len(related_traits) == p_len:
        p_len = len(related_traits)
        related_traits = list(filter(
            lambda trait: not any([
                t.value[1] in trait.__bases__
                for t in filter(lambda oth: oth is not trait, related_traits)
            ]
            ), related_traits)
        )

    return related_traits[0].value[0]
