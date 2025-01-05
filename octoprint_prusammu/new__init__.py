PLUGIN_NAME = "prusammu"

class PrusaMMUPlugin(octoprint.plugin.StartupPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.EventHandlerPlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.SettingsPlugin):

  def __init__(self):
    pass

  # ======== Startup ========

  def on_after_startup(self):
    self._log("on_after_startup")

    # ======== TemplatePlugin ========

  def get_template_configs(self):
    return [
      dict(type="settings", custom_bindings=False)
    ]

  # ======== AssetPlugin ========

  def get_assets(self):
    return dict(
      js=["mmuErrors.js", "mmuProgress.js", "prusammu.js", "colorPick.js"],
      css=["prusammu.css", "colorPick.css"],
    )

  # ======== SimpleApiPlugin ========

  def get_api_commands(self):
    return dict(
      select=["choice"],
      getmmu=[],
    )

  def on_api_command(self, command, data):
    pass

  # ======== Printer Firmware Hooks ========
  # https://docs.octoprint.org/en/master/plugins/hooks.html#firmware_info_hook

  def firmware_info_hook(self, comm_instance, firmware_name, firmware_data, *args, **kwargs):
    pass

  # ======== Gcode Hooks ========
  # https://docs.octoprint.org/en/master/plugins/hooks.html#octoprint-comm-protocol-gcode-phase

  def gcode_queuing_hook(self, comm, phase, cmd, cmd_type, gcode,
                         subcode=None, tags=None, *args, **kwarg):
    pass

  # Listen for MMU events and update the nav to reflect it
  def gcode_received_hook(self, comm, line, *args, **kwargs):
    pass

  def gcode_sent_hook(self, comm, phase, cmd, cmd_type, gcode,
                      subcode=None, tags=None, *args, **kwarg):
    pass

  # ======== EventHandlerPlugin ========

  def register_custom_events(*args, **kwargs):
    return [
      PluginEventKeys.REGISTER_MMU_CHANGE,
      PluginEventKeys.REGISTER_MMU_CHANGED, # for other plugins
      PluginEventKeys.REGISTER_REFRESH_NAV,
      PluginEventKeys.REGISTER_SHOW_PROMPT,
    ]

  def on_event(self, event, payload=None):
    pass

   # ======== SettingsPlugin ========

  def get_settings_defaults(self):
    return dict(
      debug=False,
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=True,
      simpleDisplayMode=False,
      advancedDisplayMode=True,
      defaultFilament=-1,
      indexAtZero=False,
      classicColorPicker=False,
      filamentSource=PLUGIN_NAME,
      filamentSources=FILAMENT_SOURCE_DEFAULT,
      filament=[
        dict(name="", color="", enabled=True, id=1),
        dict(name="", color="", enabled=True, id=2),
        dict(name="", color="", enabled=True, id=3),
        dict(name="", color="", enabled=True, id=4),
        dict(name="", color="", enabled=True, id=5),
      ],
      filamentMap=[dict(id=0), dict(id=1), dict(id=2), dict(id=3), dict(id=4)],
      useFilamentMap=False,
      enablePrompt=True,
      prusaVersion="",
    )

  def on_settings_save(self, data):
    pass

  # ======== SoftwareUpdatePlugin ========
  # https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
  
  def get_update_information(self):
    githubUrl = "https://github.com/jukebox42/Octoprint-PrusaMMU"
    pipPath = "/releases/download/{target_version}/Octoprint-PrusaMmu.zip"
    # Define the configuration for your plugin to use with the Software Update.
    return dict(
	    PrusaMMU=dict(
        displayName=PLUGIN_NAME,
        displayVersion=self._plugin_version,

        # version check: github repository
        type="github_release",
        user="jukebox42",
        repo="Octoprint-PrusaMMU",
        current=self._plugin_version,

        # update method: pip
        pip=githubUrl+pipPath
      )
    )
  
    # ======== Misc ========

  def _log(self, msg, obj=None, debug=False):
    try:
      if not debug:
        return self._logger.info(msg)
      
      if SettingsKeys.DEBUG not in self.config or not self.config[SettingsKeys.DEBUG]:
        return
      
      if obj is not None:
        msg = "{} {}".format(msg, dumps(obj))
      self._logger.debug(msg)
      self._plugin_manager.send_plugin_message(
        self._identifier,
        dict(
          action="debug",
          msg=msg,
        )
      )
    except:
      pass

__plugin_name__ = "Prusa MMU"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = PrusaMMUPlugin()
__plugin_hooks__ = {
  "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
  "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received_hook,
  "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gcode_sent_hook,
  "octoprint.comm.protocol.firmware.info": __plugin_implementation__.firmware_info_hook,
  "octoprint.events.register_custom_events":  __plugin_implementation__.register_custom_events,
  "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
}

