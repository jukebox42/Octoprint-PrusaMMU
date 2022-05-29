# coding=utf-8
from __future__ import absolute_import, unicode_literals
import octoprint.plugin
from threading import Timer
import re

from octoprint.server import user_permission

import flask
from flask_babel import gettext

DEFAULT_TIMEOUT = 30
TAG_PREFIX = "prusaMMUPlugin:"
TIMEOUT_TAG = TAG_PREFIX + "timeout"

class PrusaMMUPlugin(octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.SettingsPlugin):

  def __init__(self):
    # Plugin Status
    self._active = False
    self._selectedFilament = None
    self._filamentChangeTriggered = False
    self._timer = None

    # MMU Status
    self.mmuState = "OK"
    self.mmuTool = ""


    # Init/Save
    self._timeout = DEFAULT_TIMEOUT
    self._useDefaultFilament = False
    self._displayActiveFilament = False
    self._defaultFilament = 1

  # ======== Startup ========

  def on_after_startup(self):
    self._logger.info("on_after_startup")
    self._set_class_vars()

  # ======== TemplatePlugin ========

  def get_template_configs(self):
    return [
      # dict(type="navbar", custom_bindings=True),
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

      if self._active is False:
        return flask.abort(409, "No active prompt")

      choice = data["choice"]
      if not isinstance(choice, int) or not choice < 5 or not choice >= 0:
        return flask.abort(400, "{!r} is not a valid value for filament choice".format(choice+1))

      self._logger.info("on_api_command" + "T" + str(choice))
      self.mmuTool = choice

      self._done_prompt("T" + str(choice))

  # ======== Prompt ========

  def _show_prompt(self):
    self._active = True
    self._timer = Timer(float(self._timeout), self._timeout_prompt)
    self._timer.start()
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="show"))

  def _timeout_prompt(self):
    self._printer.commands("Tx", tags={TIMEOUT_TAG})
    self._clean_up_prompt()

  def _done_prompt(self, command, tags=set()):
    self._logger.info("_done_prompt " + command)
    self._selectedFilament = command
    self._filamentChangeTriggered = True
    self._clean_up_prompt()

  def _clean_up_prompt(self):
    self._timer.cancel()
    self._active = False
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="close"))
    self._printer.set_job_on_hold(False)

  # ======== Nav Updater ========

  def _update_nav(self, state):
    if state == self.mmuState:
      return
    self.mmuState = state

    # TODO: Save this somewhere so it can be fetched on load. Who keeps an octoprint open?
    # self._logger.info("_update_nav S: " + self.mmuState + " T: " + str(self.mmuTool))

    self._plugin_manager.send_plugin_message(
      self._identifier,
      dict(
        action="nav",
        tool=self.mmuTool,
        state=self.mmuState
      )
    )

  # ======== Hooks ========

  def gcode_queuing_hook(self, comm, phase, cmd, cmd_type, gcode,
                         subcode=None, tags=None, *args, **kwarg):
    # only react to tool change commands
    if not cmd.startswith("Tx") and not cmd.startswith("M109"):
      return

    if TIMEOUT_TAG in tags:
      return

    if cmd.startswith("M109"):
      # self._logger.info(
      #   "gcode_queuing_hook " +
      #   cmd + " " +
      #   str(self._selectedFilament) + " " +
      #   str(self._filamentChangeTriggered)
      # )
      if self._selectedFilament is not None and self._filamentChangeTriggered:
        tool_cmd = self._selectedFilament
        self.mmuTool = tool_cmd
        self._selectedFilament = None
        self._filamentChangeTriggered = False
        # self._logger.info("gcode_queuing_hook_M109 " + tool_cmd)
        return[(cmd,), (tool_cmd,)]
      else:
        return

    # Prompt for filament change
    if cmd.startswith("Tx"):
      self._logger.info("gcode_queuing_hook " + cmd)
      if self._printer.set_job_on_hold(True):
        self._show_prompt()

    return None,

  def gcode_received_hook(self, comm, line, *args, **kwargs):
    if "paused for user" in line:
      self._update_nav("PAUSED_USER")
    elif "MMU not responding" in line:
      self._update_nav("ATTENTION")
    elif "MMU - ENABLED" in line:
      self._update_nav("OK")
    elif "MMU starts responding" in line:
      self._update_nav("OK")
    elif "Unloading finished" in line:
      self.mmuTool = ""
      self._update_nav("UNLOADING")
    elif "MMU can_load" in line:
      self._update_nav("LOADING")
    elif "OO succeeded" in line:
      self._update_nav("LOADED")

    return line

  # ======== SettingsPlugin ========

  def get_settings_defaults(self):
    return dict(
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=True,
      defaultFilament=-1,
      filament=[
        dict(name="", color="", id=1), # 1
        dict(name="", color="", id=2), # 2
        dict(name="", color="", id=3), # 3
        dict(name="", color="", id=4), # 4
        dict(name="", color="", id=5)  # 5
      ]
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
    self._set_class_vars()

  def _set_class_vars(self):
    self._timeout = self._settings.get_int(["timeout"])
    self._useDefaultFilament = self._settings.get_boolean(["useDefaultFilament"])
    self._displayActiveFilament = self._settings.get_boolean(["displayActiveFilament"])
    self._defaultFilament = self._settings.get_int(["defaultFilament"])


__plugin_name__ = "Prusa MMU"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = PrusaMMUPlugin()
__plugin_hooks__ = {
  "octoprint.comm.protocol.gcode.queuing": __plugin_implementation__.gcode_queuing_hook,
  "octoprint.comm.protocol.gcode.received": __plugin_implementation__.gcode_received_hook,
}