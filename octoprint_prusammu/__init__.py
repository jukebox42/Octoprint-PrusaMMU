# coding=utf-8
from __future__ import absolute_import, unicode_literals
from threading import Timer
from json import dumps
from flask import abort
from re import search

import octoprint.plugin
from octoprint.server import user_permission
from octoprint.events import Events

from octoprint_prusammu.common.Mmu import MmuStates, MmuKeys, DEFAULT_MMU_STATE
from octoprint_prusammu.common.PluginEventKeys import PluginEventKeys
from octoprint_prusammu.common.SettingsKeys import SettingsKeys
from octoprint_prusammu.common.StateKeys import StateKeys, DEFAULT_STATE

# === Constants ===
DEFAULT_TIMEOUT = 30
PLUGIN_NAME = "prusammu"
TAG_PREFIX = "prusaMMUPlugin:"
TIMEOUT_TAG = "{}timeout".format(TAG_PREFIX)
DEFAULT_M109 = "M109"
FILAMENT_SOURCE_DEFAULT = [
  dict(name="Prusa MMU", id=PLUGIN_NAME),
  # dict(name="GCode", id="gcode"),
]


class PrusaMMUPlugin(octoprint.plugin.StartupPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.EventHandlerPlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.SettingsPlugin):

  def __init__(self):
    # Dialog Status Variables
    self.timer = None
    self.states = DEFAULT_STATE

    # MMU Status - Used to display MMU data in the navbar
    self.mmu = DEFAULT_MMU_STATE

    # Local Settings Config
    self.config = dict(
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=False,
      defaultFilament=-1,
      filamentSource=PLUGIN_NAME,
      filamentSources=[],
    )

  # ======== Startup ========

  def on_after_startup(self):
    self._log("on_after_startup")
    
    try:
      # After startup set the sources we have available
      # TODO: Move this out of settings
      sources = FILAMENT_SOURCE_DEFAULT
      filamentManager = self._plugin_manager.get_plugin_info("filamentmanager")
      if filamentManager is not None and filamentManager.enabled:
        self._log("Found Filament Manager")
        sources.append(dict(name="Filament Manager", id="filamentManager"))

      spoolManager = self._plugin_manager.get_plugin_info("SpoolManager")
      if spoolManager is not None and spoolManager.enabled:
        self._log("Found Spool Manager")
        sources.append(dict(name="Spool Manager", id="spoolManager"))

      self._settings.set([SettingsKeys.FILAMENT_SOURCES], sources)
      self._settings.save()
    except Exception as e:
      self._log("Failed to load sources {}".format(str(e)))

    self._refresh_config()
    self.mmu = DEFAULT_MMU_STATE

  # ======== TemplatePlugin ========

  def get_template_configs(self):
    return [
      dict(type="settings", custom_bindings=False)
    ]

  # ======== AssetPlugin ========

  def get_assets(self):
    return dict(
      js=["prusammu.js", "colorPick.js"],
      css=["prusammu.css", "colorPick.css"],
    )

  # ======== SimpleApiPlugin ========

  def get_api_commands(self):
    return dict(
      select=["choice"],
      getmmu=[]
    )

  def on_api_command(self, command, data):
    if command == "select":
      if not user_permission.can():
        return abort(403, "Insufficient permissions")

      if self.states[StateKeys.ACTIVE] is False:
        return abort(409, "No active prompt")

      choice = data["choice"]
      if not isinstance(choice, int) or not choice < 5 or not choice >= 0:
        return abort(400, "{} is not a valid value for filament choice".format(choice+1))

      self._log("on_api_command T{}".format(choice), debug=True)
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(tool=choice))
      self._done_prompt(choice)

    if command == "getmmu":
      if not user_permission.can():
        return abort(403, "Insufficient permissions")
      
      self._fire_event(PluginEventKeys.REFRESH_NAV)


  # ======== Prompt ========

  def _show_prompt(self):
    self.states[StateKeys.ACTIVE] = True
    self.timer = Timer(float(self.config[SettingsKeys.TIMEOUT]), self._timeout_prompt)
    self.timer.start()
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="show"))

  def _timeout_prompt(self):
    # Handle if the user had a default filament
    if (
      self.config[SettingsKeys.USE_DEFAULT_FILAMENT] and
      self.config[SettingsKeys.DEFAULT_FILAMENT] > -1
    ):
      self.states[StateKeys.SELECTED_FILAMENT] = self.config[SettingsKeys.DEFAULT_FILAMENT]
    else:
      self._printer.commands("Tx", tags={TIMEOUT_TAG})
    self._clean_up_prompt()

  def _done_prompt(self, command, tags=set()):
    self._log("_done_prompt {}".format(command), debug=True)
    self.states[StateKeys.SELECTED_FILAMENT] = command
    self._clean_up_prompt()

  def _clean_up_prompt(self):
    self.timer.cancel()
    self.states[StateKeys.ACTIVE] = False
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="close"))
    self._printer.set_job_on_hold(False)

  # ======== Nav Updater ========

  def _update_navbar(self):
    self._log("update_navbar:", obj=self.mmu, debug=True)
    self._plugin_manager.send_plugin_message(
      self._identifier,
      dict(
        action="nav",
        tool=self.mmu[MmuKeys.TOOL],
        previousTool=self.mmu[MmuKeys.PREV_TOOL],
        state=self.mmu[MmuKeys.STATE]
      )
    )

  # ======== Gcode Hooks ========
  # https://docs.octoprint.org/en/master/plugins/hooks.html#octoprint-comm-protocol-gcode-phase
  # Hint: these are linked at the bottom of the file __plugin_hooks__

  def gcode_queuing_hook(self, comm, phase, cmd, cmd_type, gcode,
                         subcode=None, tags=None, *args, **kwarg):
    m109Command = self.config[SettingsKeys.M109_COMMAND]
    # only react to tool change commands and ignore everything if they dont want the dialog
    if not cmd.startswith("Tx") and not cmd.startswith(m109Command):
      return # passthrough

    # This line right here is how we handle not prompting the user again if they timeout
    if TIMEOUT_TAG in tags:
      return # passthrough

    if cmd.startswith(m109Command):
      self._log("gcode_queuing_hook_M109 command: {}".format(cmd), debug=True)
      if self.states[StateKeys.SELECTED_FILAMENT] is not None:
        tool_cmd = "T{}".format(self.states[StateKeys.SELECTED_FILAMENT])
        self._fire_event(PluginEventKeys.MMU_CHANGE,
                        dict(tool=self.states[StateKeys.SELECTED_FILAMENT]))
        self.states[StateKeys.SELECTED_FILAMENT] = None
        self._log("gcode_queuing_hook_M109 tool: {}".format(tool_cmd), debug=True)
        return[(cmd,), (tool_cmd,)] # rewrite (append tool command)
      else:
        return # passthrough

    # Prompt for filament change
    if cmd.startswith("Tx"):
      self._log("gcode_queuing_hook {}".format(cmd), debug=True)
      if self._printer.set_job_on_hold(True):
        self._fire_event(PluginEventKeys.SHOW_PROMPT)
      return None, # suppress

    return # passthrough

  # Listen for MMU2 events and update the nav to reflect it
  def gcode_received_hook(self, comm, line, *args, **kwargs):
    if "paused for user" in line:
      # The printer will spam pause messages directly after an attention so ignore them
      if self.mmu[MmuKeys.STATE] == MmuStates.ATTENTION:
        return line
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.PAUSED_USER))
    elif "MMU => 'start'" in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.STARTING))
    elif "MMU not responding" in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.ATTENTION))
    elif "MMU - ENABLED" in line or "MMU starts responding" in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.OK))
    elif "MMU can_load" in line or "Unloading finished" in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.LOADING))
    # elif "mmu_get_response - begin move: unload" in line:
    #   self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.UNLOADING))
    elif "OO succeeded" in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.LOADED))

    return line

  def gcode_sent_hook(self, comm, phase, cmd, cmd_type, gcode,
                      subcode=None, tags=None, *args, **kwarg):
    # only react to tool change commands
    if (
      not cmd.startswith("T0") and not cmd.startswith("T1") and not cmd.startswith("T2")
      and not cmd.startswith("T3") and not cmd.startswith("T4") 
    ):
      return

    # Catch when the gcode sends a tool number, this happens when it's set to print in multi
    try:
      x = search(r"T(\d)", cmd)
      tool = x.group(1)

      # This indicates the tool was already loaded and we tried to load it again. The printer should
      # ignore this event so we will too. The nav should already represent this data anyways.
      if self.mmu[MmuKeys.STATE] == MmuStates.LOADED and self.mmu[MmuKeys.TOOL] == tool:
        return

      # Show unloading if there's already a tool loaded and it's not the same tool
      if self.mmu[MmuKeys.STATE] == MmuStates.LOADED and self.mmu[MmuKeys.TOOL] != tool:
        self._fire_event(PluginEventKeys.MMU_CHANGE,
                        dict(state=MmuStates.UNLOADING,
                             tool=tool,
                             previousTool=self.mmu[MmuKeys.TOOL]))
        return

      # Otherwise assume it's a first time load
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(tool=tool))
      self._log("gcode_sent_hook Tool: {} CMD: {}".format(tool, cmd), debug=True)
    except:
      pass

    return

  # ======== EventHandlerPlugin ========

  def _fire_event(self, key, payload=None):
    self._event_bus.fire(key, payload=payload)


  def register_custom_events(*args, **kwargs):
    return [
      PluginEventKeys.REGISTER_MMU_CHANGE,
      PluginEventKeys.REGISTER_MMU_CHANGED, # for other plugins
      PluginEventKeys.REGISTER_REFRESH_NAV,
      PluginEventKeys.REGISTER_SHOW_PROMPT,
    ]

  def on_event(self, event, payload=None):
    # This is fired at the end of the change event, we dont need it but other plugins might
    # if event == PluginEventKeys.MMU_CHANGED:
    #   self._log("on_event {} with".format(event, obj=payload, debug=True)
    #   return

    # Fired any time we detect a command that would update something about the MMU
    if event == PluginEventKeys.MMU_CHANGE:
      self._log("on_event {} with".format(event), obj=payload, debug=True)
      if MmuKeys.STATE not in payload:
        payload[MmuKeys.STATE] = self.mmu[MmuKeys.STATE]
      if MmuKeys.TOOL not in payload:
        payload[MmuKeys.TOOL] = self.mmu[MmuKeys.TOOL]
      if MmuKeys.PREV_TOOL not in payload:
        payload[MmuKeys.PREV_TOOL] = self.mmu[MmuKeys.PREV_TOOL]
      # failsafe so we dont constantly spam state changes
      if (
        self.mmu[MmuKeys.STATE] == payload[MmuKeys.STATE] and
        self.mmu[MmuKeys.TOOL] == payload[MmuKeys.TOOL] and
        self.mmu[MmuKeys.PREV_TOOL] == payload[MmuKeys.PREV_TOOL]
      ):
        return
      self.mmu = dict(
        state=None if MmuKeys.STATE not in payload else payload[MmuKeys.STATE],
        tool=None if MmuKeys.TOOL not in payload else payload[MmuKeys.TOOL],
        previousTool=None if MmuKeys.PREV_TOOL not in payload else payload[MmuKeys.PREV_TOOL])
      self._fire_event(PluginEventKeys.MMU_CHANGED, self.mmu)
      self._update_navbar()
      return

    # Fired to cause a refresh event on the UI
    if event == PluginEventKeys.REFRESH_NAV:
      self._log("on_event {}".format(event), debug=True)
      self._update_navbar()
      return

    # Fired to prompt the user to select a filament
    if event == PluginEventKeys.SHOW_PROMPT:
      self._log("on_event {}".format(event), debug=True)
      self._show_prompt()
      return

    # Handle disconenced event to set the mmu to Not Found (no printer...)
    if event == "Disconnected":
      self._log("on_event {}".format(event), debug=True)
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                      dict(state= MmuStates.NOT_FOUND, tool="", previousTool=""))

    # Handle terminal states when printer is no longer printing to reset the MMU
    if (
      event == Events.PRINT_DONE or
      event == Events.PRINT_CANCELLED or
      (event == Events.PRINT_FAILED and self.mmu[MmuKeys.STATE] != MmuStates.ATTENTION)
    ):
      self._log("on_event {}".format(event), debug=True)
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                      dict(state=MmuStates.OK, tool="", previousTool=""))

  # ======== SettingsPlugin ========

  def get_settings_defaults(self):
    return dict(
      debug=False,
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=True,
      simpleDisplayMode=False,
      defaultFilament=-1,
      indexAtZero=False,
      classicColorPicker=False,
      m109Command=DEFAULT_M109,
      filamentSource=PLUGIN_NAME,
      filamentSources=FILAMENT_SOURCE_DEFAULT,
      filament=[
        dict(name="", color="", enabled=True, id=1),
        dict(name="", color="", enabled=True, id=2),
        dict(name="", color="", enabled=True, id=3),
        dict(name="", color="", enabled=True, id=4),
        dict(name="", color="", enabled=True, id=5),
      ],
      gcodeFilament=[
        dict(name="", color="", id=1),
        dict(name="", color="", id=2),
        dict(name="", color="", id=3),
        dict(name="", color="", id=4),
        dict(name="", color="", id=5),
      ],
    )

  def on_settings_save(self, data):
    # ensure timeout is correct
    try:
      if SettingsKeys.TIMEOUT not in data:
        data[SettingsKeys.TIMEOUT] = self._settings.get_int([SettingsKeys.TIMEOUT])
      data[SettingsKeys.TIMEOUT] = int(data[SettingsKeys.TIMEOUT])

      if data[SettingsKeys.TIMEOUT] < 1:
        data[SettingsKeys.TIMEOUT] = DEFAULT_TIMEOUT
    except:
      data[SettingsKeys.TIMEOUT] = DEFAULT_TIMEOUT

    if SettingsKeys.M109_COMMAND not in data or data[SettingsKeys.M109_COMMAND] == "":
      data[SettingsKeys.M109_COMMAND] = DEFAULT_M109

    # Always remember gcode filament, we dont care if it's stale it'll be refreshed on load
    # TODO: load this data on print load or something. i dunno good luck.
    if SettingsKeys.GCODE_FILAMENT not in data:
      data[SettingsKeys.GCODE_FILAMENT] = self._settings.get([SettingsKeys.GCODE_FILAMENT])

    self._log("on_settings_save", debug=True)

    # save settings
    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
    self._refresh_config()

  def _refresh_config(self):
    self.config[SettingsKeys.DEBUG] = self._settings.get_boolean([SettingsKeys.DEBUG])
    self.config[SettingsKeys.SIMPLE_DISPLAY_MODE] = self._settings.get_boolean([
      SettingsKeys.SIMPLE_DISPLAY_MODE])

    self.config[SettingsKeys.TIMEOUT] = self._settings.get_int([SettingsKeys.TIMEOUT])
    self.config[SettingsKeys.USE_DEFAULT_FILAMENT] = self._settings.get_boolean([
      SettingsKeys.USE_DEFAULT_FILAMENT])
    self.config[SettingsKeys.DEFAULT_FILAMENT] = self._settings.get_int([
      SettingsKeys.DEFAULT_FILAMENT])

    self.config[SettingsKeys.DISPLAY_ACTIVE_FILAMENT] = self._settings.get_boolean([
      SettingsKeys.DISPLAY_ACTIVE_FILAMENT])
    self.config[SettingsKeys.FILAMENT_SOURCE] = self._settings.get([SettingsKeys.FILAMENT_SOURCE])
    self.config[SettingsKeys.FILAMENT_SOURCES] = self._settings.get([SettingsKeys.FILAMENT_SOURCES])
    self.config[SettingsKeys.M109_COMMAND] = self._settings.get([SettingsKeys.M109_COMMAND])

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
    if debug:
      if self.config[SettingsKeys.DEBUG]:
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
    else:
      self._logger.info(msg)


__plugin_name__ = "Prusa MMU"
__plugin_pythoncompat__ = ">=3,<4"
__plugin_implementation__ = PrusaMMUPlugin()
__plugin_hooks__ = {
  "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
  "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received_hook,
  "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gcode_sent_hook,
  "octoprint.events.register_custom_events":  __plugin_implementation__.register_custom_events,
  "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
}
