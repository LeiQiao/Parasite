class Plugin:
    before_load_methods = []
    after_load_methods = []
    before_install_methods = []
    after_install_methods = []

    def __init__(self, plugin_name=None, manifest=None):
        self.plugin_name = plugin_name
        self.manifest = manifest

    @staticmethod
    def before_load(f):
        if f not in Plugin.before_load_methods:
            Plugin.before_load_methods.append(f)

    @staticmethod
    def after_load(f):
        if f not in Plugin.after_load_methods:
            Plugin.after_load_methods.append(f)

    def on_before_load(self):
        for f in Plugin.before_load_methods:
            f(self)

    def on_after_load(self):
        for f in Plugin.after_load_methods:
            f(self)

    # Overridable -- handle load plugin event
    def on_load(self):
        pass

    # Overridable -- handle unload plugin event
    def on_unload(self):
        pass

    @staticmethod
    def before_install(f):
        if f not in Plugin.before_install_methods:
            Plugin.before_install_methods.append(f)

    @staticmethod
    def after_install(f):
        if f not in Plugin.after_install_methods:
            Plugin.after_install_methods.append(f)

    def on_before_install(self):
        for f in Plugin.before_install_methods:
            f(self)

    def on_after_install(self):
        for f in Plugin.after_install_methods:
            f(self)

    # Overridable -- handle install plugin event
    def on_install(self):
        pass

    # Overridable -- handle upgrade plugin event
    def on_upgrade(self, old_version):
        pass

    # Overridable -- handle uninstall plugin event
    def on_uninstall(self, erase_all_data=False):
        pass
