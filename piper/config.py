from os import getcwd

from traitlets import Unicode, List, default, Bool, Integer
from traitlets.config import SingletonConfigurable, Application, Configurable

from piper.drivers.traitlets import BoltConnection, ExistingFile, \
    SelfInstantiatingInstance, ExistingDirectory


class ShellLoggingConfiguration(Configurable):
    overwrite = Bool(default_value=True).tag(config=True)
    sleep = Integer(default_value=4).tag(config=True)

    def shell_dict(self):
        return {
            "overwrite": self.overwrite,
            "sleep": self.sleep
        }


class SingularityConfiguration(Configurable):
    image = ExistingFile(
        default_value=None, allow_none=True
    ).tag(config=True)
    bind_paths = List(
        trait=ExistingDirectory, default_value=[]
    ).tag(config=True)

    def shell_dict(self):
        return {
            "image": self.image,
            "bind_paths": self.bind_paths
        }


class PiperConfig(SingletonConfigurable):
    neo4j_db_connection = SelfInstantiatingInstance(
        BoltConnection, kw={
            'username': 'neo4j',
            'password': 'neo4j',
            'address': ('localhost', 7687)
        }
    ).tag(config=True)

    shell_logging = SelfInstantiatingInstance(
        ShellLoggingConfiguration
    ).tag(config=True)

    singularity = SelfInstantiatingInstance(
        SingularityConfiguration
    ).tag(config=True)

    def __init__(self, **kwargs):
        self.neo4j_db_connection.parent = self
        self.shell_logging.parent = self
        self.singularity.parent = self
        super().__init__(**kwargs)

    def generate_shell_config(self):
        return {
            **self.singularity.shell_dict(),
            **self.shell_logging.shell_dict()
        }


class PiperConfigApplication(Application):
    name = Unicode(u'piper configuration service')
    description = Unicode(u'Small underlying service to piper pipelining '
                          u'utility, propagating global configuration '
                          u'options to sub-packages')
    # TODO : change this version to follow setup.py and global version of
    #        package when it will be exported to its own project
    version = Unicode(u'0.1')
    classes = List()

    @default('classes')
    def _classes_default(self):
        return [
            self.__class__, PiperConfig
        ]

    def __init__(self, **kwargs):
        global piper_config
        super().__init__(**kwargs)
        self.load_config_file("piper_config", getcwd())
        self.initialize()
        piper_config = PiperConfig.instance(parent=self)


piper_config = None
PiperConfigApplication.launch_instance()
config_manager = PiperConfigApplication.instance()
print(config_manager.document_config_options())
print("Config files {}".format(config_manager.loaded_config_files))
