class Plugin:
    before_load_methods = []
    after_load_methods = []
    before_unload_methods = []

    def __init__(self, plugin_name=None, manifest=None, plugin_path=None):
        self.plugin_name = plugin_name
        self.manifest = manifest
        self.plugin_path = plugin_path

    @staticmethod
    def before_load(f):
        if f not in Plugin.before_load_methods:
            Plugin.before_load_methods.append(f)

    @staticmethod
    def after_load(f):
        if f not in Plugin.after_load_methods:
            Plugin.after_load_methods.append(f)

    @staticmethod
    def before_unload(f):
        if f not in Plugin.before_unload_methods:
            Plugin.before_unload_methods.append(f)

    def on_before_load(self):
        for f in Plugin.before_load_methods:
            f(self)

    def on_after_load(self):
        for f in Plugin.after_load_methods:
            f(self)

    def on_before_unload(self):
        for f in Plugin.before_unload_methods:
            f(self)

    # Overridable -- handle load plugin event
    def on_load(self):
        pass

    # Overridable -- handle unload plugin event
    def on_unload(self):
        pass
