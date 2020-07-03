from neomodel import ArrayProperty, StringProperty, BooleanProperty, \
    RelationshipFrom, RelationshipTo, DateTimeProperty, Relationship, One, \
    IntegerProperty, StructuredRel, OneOrMore, UniqueIdProperty, StructuredNode

from piper.drivers.neo4j import config_db

config_db()


class BaseModel(StructuredNode):
    __abstract_node__ = True
    uid = UniqueIdProperty(label=True)
    name = StringProperty(index=True)
    pass


class PiperNode(BaseModel):
    __abstract_node__ = True
    uuid = StringProperty(unique_index=True)
    type = StringProperty(index=True)


class GraphSubItem(PiperNode):
    __abstract_node__ = True
    graph_id = Relationship('Pipeline', 'BELONGS_TO', cardinality=One)


class CommNode(GraphSubItem):
    __abstract_node__ = True
    pass


class PipelineItem(GraphSubItem):
    __abstract_node__ = True
    creation_time = DateTimeProperty(True)
    start_time = DateTimeProperty()
    end_time = DateTimeProperty()


class Subscriber(StructuredRel):
    name = StringProperty()
    start_time = DateTimeProperty(True)
    end_time = DateTimeProperty()


class ExecutorModel(BaseModel):
    pipeline = Relationship('Pipeline', 'EXECUTES', cardinality=One)
    results = RelationshipFrom('Channel', 'PROVIDES', model=Subscriber)


class Channel(CommNode):
    keys = ArrayProperty(StringProperty())
    broadcast = BooleanProperty(default=False)

    subscribers_in = RelationshipFrom(
        'CommNode', 'PROVIDES', model=Subscriber
    )
    subscribers_out = RelationshipTo(
        'CommNode', 'PROVIDES', model=Subscriber
    )

    creation_time = DateTimeProperty(True)
    start_time = DateTimeProperty()
    end_time = DateTimeProperty()


class Unit(PipelineItem, CommNode):
    log_file = StringProperty()
    process = Relationship('Process', 'RUNS')

    subscriber_in = RelationshipFrom(
        'CommNode', 'PROVIDES', model=Subscriber#, cardinality=One
    )
    subscriber_out = RelationshipTo(
        'CommNode', 'PROVIDES', model=Subscriber#, cardinality=One
    )


class Layer(PipelineItem):
    channel_in = RelationshipFrom('Channel', 'PROVIDES')
    channel_out = RelationshipTo('Channel', 'PROVIDES')

    inter_item_channels = Relationship('Channel', 'MANAGES')
    hidden_channels = Relationship('Channel', 'MANAGES')
    items = Relationship('PipelineItem', 'MANAGES')


class Process(GraphSubItem):
    required_inputs = ArrayProperty(StringProperty())
    optional_inputs = ArrayProperty(StringProperty(), required=False)
    n_cores = IntegerProperty(index=True, default=1)
    process_executor = StringProperty()


class Pipeline(BaseModel):
    initialized = BooleanProperty(default=False)

    channel_in = Relationship('Channel', 'PROVIDES')
    channel_out = Relationship('Channel', 'PROVIDES')

    items = Relationship('PipelineItem', 'CONTAINS', OneOrMore)

    creation_time = DateTimeProperty(True)
    start_time = DateTimeProperty()
    end_time = DateTimeProperty()
