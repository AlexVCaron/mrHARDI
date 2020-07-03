from piper.drivers.neo4j import transaction_manager
from piper.graph.models import GraphSubItem, ExecutorModel
from piper.graph.traits import ModelTraits, get_all_parents


class ModelProfiler:
    def __init__(self, pipeline_model, name, close_on_exit):
        self._name = name
        self._pipeline_model = pipeline_model
        self._close_exit = close_on_exit

    @property
    def name(self):
        return self._name


class StatsManager:
    def __init__(self, executor, close_on_exit=True):
        self._executor = executor
        self._executor_model = None
        self._close_exit = close_on_exit

    def __enter__(self):
        self._initialize_graph()
        return ModelProfiler(
            self._executor_model.pipeline.single(),
            "{}_profiler".format(self._executor.pipeline.name),
            self._close_exit
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._close_exit:
            nodes = GraphSubItem.nodes.has(
                graph_id=self._executor_model.pipeline.all()
            )
            for node in nodes:
                node.delete()

    def _initialize_graph(self):
        executor_entity = self._executor.serialize
        self._executor_model = self._submit_executor(executor_entity)

        pipeline_entity = self._executor.pipeline.serialize
        entities = self._nested_dicts_to_list(pipeline_entity)

        pipeline_model = self._submit_pipeline(pipeline_entity)

        self._executor_model.pipeline.connect(pipeline_model)

        channel_models, comm_sub_map, sub_rel_map = self._submit_channels(
            self._filter_entities(ModelTraits.CHANNEL, entities)
        )

        unit_models, comm_sub_map, sub_rel_map = self._submit_units(
            self._filter_entities(ModelTraits.UNIT, entities),
            comm_sub_map, sub_rel_map
        )

        process_models = self._submit_processes(
            self._filter_entities(ModelTraits.PROCESS, entities)
        )

        layer_models = self._submit_layers(
            self._filter_entities(ModelTraits.LAYER, entities)
        )

        self._create_subscriber_connections(
            comm_sub_map, sub_rel_map
        )

        result_sub_id = executor_entity["results"]["uuid"]
        sub_rel_map[result_sub_id] = executor_entity["results"]
        comm_sub_map[result_sub_id]["to"].append(self._executor_model)

        self._populate_relationships(
            pipeline_entity, entities, channel_models,
            unit_models, process_models, layer_models
        )

    def _populate_relationships(
        self, pipeline_entity, entities, channels, units, processes, layers
    ):
        with transaction_manager():
            pipeline = self._executor_model.pipeline.single()

            pipeline.channel_in.connect(
                channels[str(pipeline_entity["channel_in"]["uuid"])]
            )
            pipeline.channel_out.connect(
                channels[str(pipeline_entity["channel_out"]["uuid"])]
            )

            pipeline_items = {**units, **layers}

            for item in pipeline_entity["items"]:
                pipeline.items.connect(pipeline_items[str(item["uuid"])])

            for unit in self._filter_entities(ModelTraits.UNIT, entities):
                units[str(unit["uuid"])].process.connect(
                    processes[str(unit["process"]["uuid"])]
                )

            for layer in self._filter_entities(ModelTraits.LAYER, entities):
                layer_model = layers[str(layer["uuid"])]
                layer_model.channel_in.connect(
                    channels[str(layer["subscriber_in"]["uuid"])]
                )
                layer_model.channel_out.connect(
                    channels[str(layer["subscriber_out"]["uuid"])]
                )

                for chan in layer["inter_item_channels"]:
                    layer_model.inter_item_channels.connect(
                        channels[str(chan["uuid"])]
                    )

                for chan in layer["hidden_channels"]:
                    layer_model.hidden_channels.connect(
                        channels[str(chan["uuid"])]
                    )

                for item in layer["items"]:
                    layer_model.items.connect(
                        pipeline_items[str(item["uuid"])]
                    )

    def _create_subscriber_connections(self, mappings, sub_mapping):
        for subscriber, mapping in mappings.items():
            for in_model in mapping["from"]:
                for out_model in mapping["to"]:
                    if isinstance(in_model, ModelTraits.CHANNEL.value[0]):
                        in_model.subscribers_out.connect(
                            out_model, sub_mapping[subscriber]
                        )
                    else:
                        in_model.subscriber_out.connect(
                            out_model, sub_mapping[subscriber]
                        )
                    if isinstance(out_model, ModelTraits.CHANNEL.value[0]):
                        out_model.subscribers_in.connect(
                            in_model, sub_mapping[subscriber]
                        )
                    else:
                        out_model.subscriber_in.connect(
                            in_model, sub_mapping[subscriber]
                        )

                    in_model.save()
                    out_model.save()

    def _filter_entities(self, trait, entities):
        # TODO : remove list above the generator
        return list(filter(
            lambda e: trait.value[1] in get_all_parents(
                e['type']
            ) + (e['type'],),
            entities
        ))

    def _submit_layers(self, layers):
        with transaction_manager():
            return {l.uuid: l for l in ModelTraits.LAYER.value[0].create(*[
                {**{
                    k: v for k, v in l.items()
                    if k not in [
                        "items", "hidden_channels", "inter_item_channels",
                        "subscriber_in", "subscriber_out"
                    ]
                }, **{
                    "graph_id": self._executor_model.pipeline.single()
                }} for l in layers
            ])}

    def _submit_processes(self, processes):
        with transaction_manager():
            return {p.uuid: p for p in ModelTraits.PROCESS.value[0].create(*[
                {**p, **{
                    "graph_id": self._executor_model.pipeline.single()
                }} for p in processes
            ])}

    def _submit_pipeline(self, pipeline):
        with transaction_manager():
            model = ModelTraits.PIPELINE.value[0](**{
                k: v for k, v in pipeline.items()
                if k not in ["channel_in", "channel_out", "items"]
            })
            model.save()

            return model

    def _submit_executor(self, executor):
        with transaction_manager():
            model = ExecutorModel(**{
                k: v for k, v in executor.items()
                if k not in ["results", "pipeline"]
            })
            model.save()

            return model

    def _submit_units(
        self, units, comm_sub_map={}, sub_rel={}
    ):
        with transaction_manager():
            units_models = ModelTraits.UNIT.value[0].create(*[
                {**{
                    k: v for k, v in u.items()
                    if k not in ["subscriber_in", "subscriber_out"]
                }, **{
                    "graph_id": self._executor_model.pipeline.single()
                }} for u in units
            ])

            sub_rel = {
                **{
                    sub["uuid"]: sub for sub in [
                        u["subscriber_in"] for u in units] + [
                        u["subscriber_out"] for u in units
                    ]
                },
                **sub_rel
            }

            comm_sub_map = {
                **{k: {"from": [], "to": []} for k in sub_rel.keys()},
                **comm_sub_map
            }

            for unit, model in zip(units, units_models):
                comm_sub_map[unit["subscriber_in"]["uuid"]]["to"].append(
                    model
                )
                comm_sub_map[unit["subscriber_out"]["uuid"]]["from"].append(
                    model
                )

            return {u.uuid: u for u in units_models}, comm_sub_map, sub_rel

    def _submit_channels(
        self, channels, comm_sub_map={}, sub_rel={}
    ):
        with transaction_manager():
            channel_models = ModelTraits.CHANNEL.value[0].create(*[
                {**{
                    k: v for k, v in c.items()
                    if k not in ["subscribers_in", "subscribers_out"]
                }, **{
                    "graph_id": self._executor_model.pipeline.single()
                }} for c in channels
            ])

            sub_rel = {
                **{
                    sub["uuid"]: sub for sub in (
                        [s for c in channels for s in c["subscribers_in"]] +
                        [s for c in channels for s in c["subscribers_out"]]
                    )
                },
                **sub_rel
            }

            comm_sub_map = {
                **{k: {"from": [], "to": []} for k in sub_rel.keys()},
                **comm_sub_map
            }

            for channel, model in zip(channels, channel_models):
                for sub in channel["subscribers_in"]:
                    comm_sub_map[sub["uuid"]]["to"].append(model)
                for sub in channel["subscribers_out"]:
                    comm_sub_map[sub["uuid"]]["from"].append(model)

            return {c.uuid: c for c in channel_models}, comm_sub_map, sub_rel

    def _nested_dicts_to_list(self, entity):
        lst = []
        keys = list(entity.keys())
        for k in keys:
            if isinstance(entity[k], dict):
                lst.extend(self._nested_dicts_to_list(entity[k]))
            elif isinstance(entity[k], (list, tuple)):
                for item in entity[k]:
                    if isinstance(item, dict):
                        lst.extend(self._nested_dicts_to_list(item))

                # entity[k] = list(filter(
                #     lambda a: not isinstance(a, dict), entity[k]
                # ))

        lst.append(entity)
        return lst
