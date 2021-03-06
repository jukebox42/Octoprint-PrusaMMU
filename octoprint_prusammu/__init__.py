# coding=utf-8
from __future__ import absolute_import, unicode_literals
from threading import Timer
import re

import octoprint.plugin
from octoprint.server import user_permission

import flask

# turning this on will cause every log write to surface as a console.log
NOISY_DEBUG = True

# === Constants ===
DEFAULT_TIMEOUT = 30
TAG_PREFIX = "prusaMMUPlugin:"
TIMEOUT_TAG = "{}timeout".format(TAG_PREFIX)

class PrusaMMUPlugin(octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.SettingsPlugin):

  def __init__(self):
    self.timer = None
    # Plugin Status
    self.states = dict(
      active=False, # Tracks when the modal is being displayed
      selectedFilament=None, # Tracks when a user selects a filament (in modal)
    )

    # MMU Status - Used to display MMU data in the navbar
    self.mmu = dict(
      state="OK",
      tool="",
    )

    # Local Settings Config
    self.config = dict(
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=False,
      defaultFilament=1,
    )

  # ======== Startup ========

  def on_after_startup(self):
    self.log("on_after_startup")
    self.refresh_config()

  # ======== TemplatePlugin ========

  def get_template_configs(self):
    return [
      dict(type="settings", custom_bindings=False)
    ]

  # ======== AssetPlugin ========

  def get_assets(self):
    return dict(
      js=["prusammu.js"]
    )

  # ======== SimpleApiPlugin ========

  def get_api_commands(self):
    return dict(
      select=["choice"],
      gettool=[]
    )

  def on_api_command(self, command, data):
    if command == "select":
      if not user_permission.can():
        return flask.abort(403, "Insufficient permissions")

      if self.states["active"] is False:
        return flask.abort(409, "No active prompt")

      choice = data["choice"]
      if not isinstance(choice, int) or not choice < 5 or not choice >= 0:
        return flask.abort(400, "{} is not a valid value for filament choice".format(choice+1))

      self.log("on_api_command T{}".format(choice))
      self.mmu["tool"] = choice

      self._done_prompt("T{}".format(choice))

  # ======== Prompt ========

  def _show_prompt(self):
    self.states["active"] = True
    self.timer = Timer(float(self.config["timeout"]), self._timeout_prompt)
    self.timer.start()
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="show"))

  def _timeout_prompt(self):
    # Handle if the user had a default filament
    if self.config["useDefaultFilament"] and self.config["defaultFilament"] > -1:
      self.states["selectedFilament"] = "T{}".format(self.config["defaultFilament"])
    else:
      self._printer.commands("Tx", tags={TIMEOUT_TAG})
    self._clean_up_prompt()

  def _done_prompt(self, command, tags=set()):
    self.log("_done_prompt {}".format(command))
    self.states["selectedFilament"] = command
    self._clean_up_prompt()

  def _clean_up_prompt(self):
    self.timer.cancel()
    self.states["active"] = False
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="close"))
    self._printer.set_job_on_hold(False)

  # ======== Nav Updater ========

  def update_navbar(self, state, force=False):
    if state == self.mmu["state"] and not force:
      return
    self.mmu["state"] = state

    # Save the mmu state into settings.
    # TODO: Settings isnt the right place to save these but this is what we've got
    self.log("update_navbar S: {} T: {}".format(self.mmu["state"], self.mmu["tool"]), True)
    try:
      self._settings.set(["mmuState"], self.mmu["state"])
      self._settings.set(["mmuTool"], self.mmu["tool"])
      self._settings.save()
    except Exception as e:
      self.log(
        "update_navbar FAILED S: {} T: {} E: {}".format(
          self.mmu["state"], self.mmu["tool"], str(e)), True)

    self._plugin_manager.send_plugin_message(
      self._identifier,
      dict(
        action="nav",
        tool=self.mmu["tool"],
        state=self.mmu["state"]
      )
    )

  # ======== Gcode Hooks ========
  # Hint: these are linked at the bottom of the file __plugin_hooks__

  def gcode_queuing_hook(self, comm, phase, cmd, cmd_type, gcode,
                         subcode=None, tags=None, *args, **kwarg):
    # only react to tool change commands
    if not cmd.startswith("Tx") and not cmd.startswith("M109"):
      return

    if TIMEOUT_TAG in tags:
      return

    if cmd.startswith("M109"):
      # self._logger.info("gcode_queuing_hook {} {}".format(cmd, self.states["selectedFilament"]))
      if self.states["selectedFilament"] is not None:
        tool_cmd = self.states["selectedFilament"]
        self.mmu["tool"] = tool_cmd
        self.states["selectedFilament"] = None
        self.log("gcode_queuing_hook_M109 {}".format(tool_cmd), True)
        return[(cmd,), (tool_cmd,)]
      else:
        return

    # Prompt for filament change
    if cmd.startswith("Tx"):
      self.log("gcode_queuing_hook {}".format(cmd), True)
      if self._printer.set_job_on_hold(True):
        self._show_prompt()
      return None,

    return

  # Listen for MMU2 events and update the nav to reflect it
  def gcode_received_hook(self, comm, line, *args, **kwargs):
    if "paused for user" in line:
      # The printer will spam pause messages directly after an attention so ignore them
      if self.mmu["state"] == "ATTENTION":
        return line
      self.update_navbar("PAUSED_USER")
    elif "MMU not responding" in line:
      self.update_navbar("ATTENTION")
    elif "MMU - ENABLED" in line:
      self.update_navbar("OK")
    elif "MMU starts responding" in line:
      self.update_navbar("OK")
    elif "Unloading finished" in line:
      self.update_navbar("UNLOADING")
    elif "MMU can_load" in line:
      self.update_navbar("LOADING")
    elif "OO succeeded" in line:
      self.update_navbar("LOADED")

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
    if cmd.startswith("T"):
      try:
        x = re.search(r"T(\d)", cmd)
        tool = x.group(1)
        self.mmu["tool"] = tool
        self.log("gcode_sent_hook T{} {}".format(tool, cmd), True)
      except:
        pass

    return

  # ======== SettingsPlugin ========

  def get_settings_defaults(self):
    return dict(
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=True,
      defaultFilament=-1,
      filament=[
        dict(name="", color="", enabled=True, id=1), # 1
        dict(name="", color="", enabled=True, id=2), # 2
        dict(name="", color="", enabled=True, id=3), # 3
        dict(name="", color="", enabled=True, id=4), # 4
        dict(name="", color="", enabled=True, id=5)  # 5
      ],
      mmuState = "OK",
      mmuTool = "",
    )

  def on_settings_save(self, data):
    # ensure timeout is correct
    try:
      data["timeout"] = int(data["timeout"])

      if data["timeout"] < 0:
        data["timeout"] = DEFAULT_TIMEOUT
    except:
      data["timeout"] = DEFAULT_TIMEOUT

    # handle default fillament setting. clear if unused
    try:
      data["useDefaultFilament"] = bool(data["useDefaultFilament"])
      if not data["useDefaultFilament"]:
        data["defaultFilament"] = -1
    except:
      data["defaultFilament"] = -1
      data["useDefaultFilament"] = False

    try:
      data["defaultFilament"] = int(data["defaultFilament"])

      if data["defaultFilament"] < 0:
        data["useDefaultFilament"] = False
    except:
      data["defaultFilament"] = -1
      data["useDefaultFilament"] = False

    # save settings
    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
    self.refresh_config()

  def refresh_config(self):
    self.config["timeout"] = self._settings.get_int(["timeout"])
    self.config["useDefaultFilament"] = self._settings.get_boolean(["useDefaultFilament"])
    self.config["displayActiveFilament"] = self._settings.get_boolean(["displayActiveFilament"])
    self.config["defaultFilament"] = self._settings.get_int(["defaultFilament"])

  def log(self, msg, debug=False):
    if not debug:
      self._logger.info(msg)
    if NOISY_DEBUG:
      self._plugin_manager.send_plugin_message(
        self._identifier,
        dict(
          action="debug",
          msg=msg
        )
      )


__plugin_name__ = "Prusa MMU"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PrusaMMUPlugin()
__plugin_hooks__ = {
  "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
  "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received_hook,
  "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.gcode_sent_hook,
}