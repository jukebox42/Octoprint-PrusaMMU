# coding=utf-8
from __future__ import absolute_import, unicode_literals
from threading import Timer
from json import dumps
from flask import abort, jsonify
from re import search

import octoprint.plugin
from octoprint.server import user_permission
from octoprint.events import Events

from octoprint_prusammu.common.Mmu import MmuStates, MmuKeys, MMU3Codes, \
  MMU3RequestCodes, MMU3ResponseCodes, MMU3MK4Commands, DEFAULT_MMU_STATE
from octoprint_prusammu.common.PluginEventKeys import PluginEventKeys
from octoprint_prusammu.common.SettingsKeys import SettingsKeys
from octoprint_prusammu.common.StateKeys import StateKeys, DEFAULT_STATE
from octoprint_prusammu.common.PrusaProfile import PrusaProfile, detect_connection_profile


# === Constants ===
DEFAULT_TIMEOUT = 30
PLUGIN_NAME = "prusammu"
TAG_PREFIX = "prusaMMUPlugin:"
TIMEOUT_TAG = "{}timeout".format(TAG_PREFIX)
FILAMENT_SOURCE_DEFAULT = [
  dict(name="Prusa MMU", id=PLUGIN_NAME),
]
TOOL_REGEX = r"^T(\d)"


class PrusaMMUPlugin(octoprint.plugin.StartupPlugin,
                     octoprint.plugin.TemplatePlugin,
                     octoprint.plugin.AssetPlugin,
                     octoprint.plugin.EventHandlerPlugin,
                     octoprint.plugin.SimpleApiPlugin,
                     octoprint.plugin.SettingsPlugin):

  def __init__(self):
    # Used for MK4 to retain the override.
    self.filamentOverride = None

    # Dialog Status Variables
    self.timer = None
    self.states = DEFAULT_STATE.copy()

    # MMU Status - Used to display MMU data in the navbar
    self.mmu = DEFAULT_MMU_STATE.copy()
    self.lastMmuAction = ""

    # Local Settings Config
    self.config = dict(
      debug=False,
      timeout=DEFAULT_TIMEOUT,
      useDefaultFilament=False,
      displayActiveFilament=False,
      defaultFilament=-1,
      filamentSource=PLUGIN_NAME,
      filamentSources=[],
      filamentMap=[],
      useFilamentMap=False,
      enablePrompt=True,
      prusaVersion="",
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
    self.mmu = DEFAULT_MMU_STATE.copy()

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
    if command == "select":
      if not user_permission.can():
        return abort(403, "Insufficient permissions")

      if self.states[StateKeys.ACTIVE] is False:
        return abort(409, "No active prompt")

      choice = data["choice"]
      if choice != "skip" and not (int(choice) < 5 or int(choice) >= 0):
        return abort(400, "{} is not a valid value for filament choice".format(choice+1))

      self._log("on_api_command T{}".format(choice), debug=True)
      if choice != "skip":
        self._fire_event(PluginEventKeys.MMU_CHANGE, dict(tool=choice))
      self._done_prompt(choice)
      return

    if command == "getmmu":
      return jsonify(self._fire_event(PluginEventKeys.REFRESH_NAV))

  # ======== Prompt ========

  def _show_prompt(self):
    self.states[StateKeys.ACTIVE] = True
    self.timer = Timer(float(self.config[SettingsKeys.TIMEOUT]), self._timeout_prompt)
    self.timer.start()
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="show"))

  def _timeout_prompt(self):
    self._log("_timeout_prompt", debug=True)
    # non-MK3 can't use default filament, instead it just defaults to whatever it was sliced with.
    if self.mmu[MmuKeys.PRUSA_VERSION] == PrusaProfile.MK3:
      # Handle if the user had a default filament
      if (
        self.config[SettingsKeys.USE_DEFAULT_FILAMENT] and
        self.config[SettingsKeys.DEFAULT_FILAMENT] > -1
      ):
        self.states[StateKeys.SELECTED_FILAMENT] = self.config[SettingsKeys.DEFAULT_FILAMENT]

      self._printer.commands("Tx", tags={TIMEOUT_TAG})

    self._clean_up_prompt()

  def _done_prompt(self, command, tags=set()):
    self._log("_done_prompt {}".format(command), debug=True)
    # If we get a skip then the user chose to skip
    if str(command) == "skip":
      self._log("_done_prompt SKIP", debug=True)
      self._clean_up_prompt()
      self._disable_mk4_remap()
      return

    self.states[StateKeys.SELECTED_FILAMENT] = command

    # MK4: Enable filament rewrite
    if (
      self.mmu[MmuKeys.PRUSA_VERSION] != PrusaProfile.MK3 and
      self.mmu[MmuKeys.PRUSA_VERSION] is not None
    ):
      self._enable_mk4_remap(command)

    self._clean_up_prompt()

  def _clean_up_prompt(self):
    self._log("_clean_up_prompt", debug=True)
    self.timer.cancel()
    self.states[StateKeys.ACTIVE] = False
    self._plugin_manager.send_plugin_message(self._identifier, dict(action="close"))
    self._printer.set_job_on_hold(False)

  # ======== MK4 Remap ========

  def _enable_mk4_remap(self, command):
    self._log("_enable_mk4_remap T{}".format(command), debug=True)
    self.filamentOverride = command

  def _disable_mk4_remap(self):
    self._log("_disable_mk4_remap", debug=True)
    self.filamentOverride = None
    return

  # ======== Nav Updater ========

  def _update_navbar(self):
    self._log("update_navbar:", obj=self.mmu, debug=True)
    self._plugin_manager.send_plugin_message(
      self._identifier,
      dict(
        action="nav",
        tool=self.mmu[MmuKeys.TOOL],
        previousTool=self.mmu[MmuKeys.PREV_TOOL],
        state=self.mmu[MmuKeys.STATE],
        response=self.mmu[MmuKeys.RESPONSE],
        responseData=self.mmu[MmuKeys.RESPONSE_DATA],
        prusaVersion=self.mmu[MmuKeys.PRUSA_VERSION],
      )
    )

  # ======== Printer Firmware Hooks ========
  # https://docs.octoprint.org/en/master/plugins/hooks.html#firmware_info_hook

  def firmware_info_hook(self, comm_instance, firmware_name, firmware_data, *args, **kwargs):
   self._process_firmware(firmware_data["MACHINE_TYPE"])

  def _process_firmware(self, machine_type, force=False):
    # Prevent detection and overwrite if it was already set (like from settings)
    version = self.mmu[MmuKeys.PRUSA_VERSION]
    if version == "" or version is None or force:
      # If we tried to set it back to auto detect then we need to ask the printer again.
      if machine_type == "" and force:
        self._printer.commands("M115")
        self.mmu[MmuKeys.PRUSA_VERSION] = None
        return

      # Figure out what Prusa version we are dealing with (defaults to MK3)
      version = detect_connection_profile(machine_type)
      self._log("_process_firmware: {}".format(version), obj=machine_type, debug=True)

    # MK4: The MMU doesn't tell us it's ok so if the printer has one assume it is.
    if version != PrusaProfile.MK3:
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.OK, prusaVersion=version))
      return
    
    # MK3: Just send the version so it's there. This probably already happened but let's go.
    self._fire_event(PluginEventKeys.MMU_CHANGE, dict(prusaVersion=version))

  # ======== Gcode Hooks ========
  # https://docs.octoprint.org/en/master/plugins/hooks.html#octoprint-comm-protocol-gcode-phase

  def gcode_queuing_hook(self, comm, phase, cmd, cmd_type, gcode,
                         subcode=None, tags=None, *args, **kwarg):
    # This line right here is how we handle not prompting the user again if they timeout
    if TIMEOUT_TAG in tags:
      return # passthrough
    
    # handle mk4 remap if it was re-mapped (This is for single filament prints)
    if self.filamentOverride is not None and search(TOOL_REGEX, cmd):
      self._log(
        "gcode_queuing_hook_T# MK4 command: {} -> T{}".format(cmd, self.filamentOverride),
        debug=True
      )
      return [("T{}".format(self.filamentOverride),),]

    # handle tool remap if enabled
    if (
       self.filamentOverride is None and self.config[SettingsKeys.USE_FILAMENT_MAP] and
       search(TOOL_REGEX, cmd)
    ):
      try:
        tool = int(search(TOOL_REGEX, cmd).group(1))
        new_tool = int(self.config[SettingsKeys.FILAMENT_MAP][tool]["id"])
        self._log("gcode_queuing_hook_T# command: {} -> T{}".format(cmd, new_tool), debug=True)
        return [("T{}".format(new_tool),),]
      except Exception as e:
        self._log("gcode_queuing_hook_T# ERROR command: {}, {}".format(cmd, str(e)), debug=True)
        return # passthrough

    # ========
    # MK4 Blocker
    # This blocks non-MK3s from proceeding. For MK4 support see above.
    # ========
    if (
      self.mmu[MmuKeys.PRUSA_VERSION] != PrusaProfile.MK3 and
      self.mmu[MmuKeys.PRUSA_VERSION] is not None
    ):
      return # passthrough

    if cmd.startswith("M1600"):
      return # passthrough

    # only react to tool change commands and ignore everything if they dont want the dialog
    if not cmd.startswith("Tx") and not cmd.startswith("M109 S"):
      return # passthrough

    if cmd.startswith("M109 S"):
      self._log("gcode_queuing_hook_M109 command: {}".format(cmd), debug=True)
      if self.states[StateKeys.SELECTED_FILAMENT] is not None:
        tool_cmd = "T{}".format(self.states[StateKeys.SELECTED_FILAMENT])
        self._fire_event(PluginEventKeys.MMU_CHANGE,
                         dict(tool=self.states[StateKeys.SELECTED_FILAMENT]))
        self.states[StateKeys.SELECTED_FILAMENT] = None
        self._log("gcode_queuing_hook_M109 tool: {}".format(tool_cmd), debug=True)
        # Rewrite and append the tool commands.
        return [(cmd,), (tool_cmd,)]
      return # passthrough

    # Prompt for filament change
    if self.config[SettingsKeys.ENABLE_PROMPT] and cmd.startswith("Tx"):
      self._log("gcode_queuing_hook {}".format(cmd), debug=True)
      if self._printer.set_job_on_hold(True):
        self._fire_event(PluginEventKeys.SHOW_PROMPT)
      return None, # suppress

    return # passthrough

  def mk4_gcode_received(self, line):
    # The MK4 is less verbose. To try and fill that gap we're faking the response and responseData
    # to try and match the information we'd expect to get. Some day I hope prusa gives us back
    # the data we had before.

    # Dedupe
    if "MMU2:" in line:
      if self.mmu[MmuKeys.LAST_LINE] == line:
        return
      self.mmu[MmuKeys.LAST_LINE] = line

    # Paused
    if MMU3MK4Commands.PAUSED_USER in line:
      self.lastMmuAction = MmuStates.PAUSED_USER
      # The printer will spam pause messages, so ignore them if we're already paused
      if self.mmu[MmuKeys.STATE] == MmuStates.PAUSED_USER:
        return
      # The printer will send pause messages directly after an attention, and attention is more
      # important, so ignore them
      elif self.mmu[MmuKeys.STATE] == MmuStates.ATTENTION:
        return
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.PAUSED_USER, response=MMU3ResponseCodes.ERROR,
                            responseData="c"))
      return

    # Errors
    if MMU3MK4Commands.ERROR in line:
      # TODO: This is a more generic error. we might be able to get something out of the bytes sent.
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.ATTENTION, response=MMU3ResponseCodes.ERROR,
                            responseData="c"))
      return
    if MMU3MK4Commands.ERROR_FILAMENT in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.ATTENTION, response=MMU3ResponseCodes.ERROR,
                            responseData="f"))
      return
    if MMU3MK4Commands.ERROR_INTERNAL in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.ATTENTION, response=MMU3ResponseCodes.ERROR,
                            responseData="d"))
      return
    if MMU3MK4Commands.ERROR_TMC in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.ATTENTION, response=MMU3ResponseCodes.ERROR,
                            responseData="e"))
      return

    # Loading
    if MMU3MK4Commands.LOADING_FINDA in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.LOADING, tool=self.mmu[MmuKeys.TOOL],
                            response=MMU3ResponseCodes.PROCESSING, responseData="5"))
      self.lastMmuAction = MmuStates.LOADING
      return
    if MMU3MK4Commands.LOADING_EXTRUDER in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.LOADING, tool=self.mmu[MmuKeys.TOOL],
                            response=MMU3ResponseCodes.PROCESSING, responseData="6"))
      self.lastMmuAction = MmuStates.LOADING
      return
    if MMU3MK4Commands.LOADING_FSENSOR in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.LOADING, tool=self.mmu[MmuKeys.TOOL],
                            response=MMU3ResponseCodes.PROCESSING, responseData="7"))
      self.lastMmuAction = MmuStates.LOADING
      return

    # Loaded, clear previous tool
    if  MMU3MK4Commands.ACTION_DONE in line and self.lastMmuAction == MmuStates.LOADING:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.LOADED, previousTool="", tool=self.mmu[MmuKeys.TOOL],
                            response=MMU3ResponseCodes.FINISHED, responseData="2"))
      self.lastMmuAction = MmuStates.LOADED
      return

    # Unloading (changing tool)
    if MMU3MK4Commands.UNLOADING in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.UNLOADING, response=MMU3ResponseCodes.PROCESSING,
                            responseData="3"))
      self.lastMmuAction = MmuStates.UNLOADING
      return

    # Unloading Final (print done)
    if MMU3MK4Commands.UNLOADING_FINAL in line:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.UNLOADING, response=MMU3ResponseCodes.PROCESSING,
                            responseData="3"))
      self.lastMmuAction = MmuStates.UNLOADING_FINAL
      return

    # Unloaded Final
    if MMU3MK4Commands.ACTION_DONE in line and self.lastMmuAction == MmuStates.UNLOADING_FINAL:
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.OK, response=MMU3ResponseCodes.FINISHED,
                            responseData="2"))
      self.lastMmuAction = MmuStates.OK
      return

    # Starting
    if search(MMU3MK4Commands.START_MATCH, line):
      # We fire them back to back because we no longer get a ready message from the MMU
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.STARTING, response=MMU3ResponseCodes.FINISHED,
                            responseData="0"))
      self._fire_event(PluginEventKeys.MMU_CHANGE,
                       dict(state=MmuStates.OK, response=MMU3ResponseCodes.FINISHED,
                            responseData="0"))
      self.lastMmuAction == MmuStates.OK
      return

    return

  def mk3_gcode_received(self, line):
    # MMU2 3.0.0
    # https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_progress_converter.cpp#L8
    # https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_protocol_logic.cpp
    # General REGEX to catch all important MMU commands
    if search(MMU3Codes.GENERAL_MATCH, line):
      # If this line is the same as the previously seen one, ignore it and return immediately,
      # otherwise it's new, so continue
      if self.mmu[MmuKeys.LAST_LINE] == line:
        return
      self.mmu[MmuKeys.LAST_LINE] = line
      # Search the line. This creates 4 matched groups. 
      # Group 1 is a single letter request code. Group 2 is the request data in hexidecimal
      # Group 3 is a single letter response code. Group 4 is the response data in hexidecimal.
      # Warning, it may not exist!
      matchedCommand = search(MMU3Codes.GROUP_MATCH, line)
      # self._log("Matched Line Info: Line: " + line + " Groups: " + matchedCommand.group(1) + "," +
      #           matchedCommand.group(2) + "," + matchedCommand.group(3) + "," +
      #           matchedCommand.group(4), debug=True)

      # If we're already at attention, and the new MMU response has an error, stay at attention and
      # add the error code, then stop checking. Otherwise the new MMU response shows that the
      # ATTENTION has cleared, so continue and get the new state.
      if (
        self.mmu[MmuKeys.STATE] == MmuStates.ATTENTION and
        matchedCommand.group(3) == MMU3ResponseCodes.ERROR
      ):
        self._fire_event(PluginEventKeys.MMU_CHANGE,
                         dict(state=MmuStates.ATTENTION, response=matchedCommand.group(3),
                              responseData=matchedCommand.group(4)))
        return

      # Load filament to nozzle
      if matchedCommand.group(1) == MMU3RequestCodes.TOOL:
        # Loading Finished, Printer is now loaded. Clear previous tool
        if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.LOADED, previousTool="",
                                response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        # Still Loading
        else:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.LOADING, tool=matchedCommand.group(2),
                                response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        return
      # Preload filament to mmu
      elif matchedCommand.group(1) == MMU3RequestCodes.LOAD:
        # Preload Finished, Printer is now idle
        if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.OK, response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        # Preload in progress
        else:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.LOADING_MMU, tool=matchedCommand.group(2),
                                response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        return
      # Unload Filament from Nozzle NOTE: Doesn't give us any tool info, so rely on T# commands to
      # give us current and previous tool info
      elif matchedCommand.group(1) == MMU3RequestCodes.UNLOAD:
        # Unload Finished, Printer is now idle
        if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.OK, response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        # Unload in progress
        else:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.UNLOADING, response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        return
      # Printer Reset, Shows up after power on
      elif matchedCommand.group(1) == MMU3RequestCodes.RESET:
        self._fire_event(PluginEventKeys.MMU_CHANGE,
                         dict(state=MmuStates.OK, response=matchedCommand.group(3),
                              responseData=matchedCommand.group(4)))
        return
      # Cut Filament
      elif matchedCommand.group(1) == MMU3RequestCodes.CUT:
        # Cutting finished, Printer is now idle
        if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.OK, response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        # Cutting in progress
        else:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.CUTTING, tool=matchedCommand.group(2),
                                response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        return
      # Eject Filament
      elif matchedCommand.group(1) == MMU3RequestCodes.EJECT:
        # Ejecting finished, Printer is now idle
        if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.OK, response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        # Ejecting in progress
        else:
          self._fire_event(PluginEventKeys.MMU_CHANGE,
                           dict(state=MmuStates.EJECTING, tool=matchedCommand.group(2),
                                response=matchedCommand.group(3),
                                responseData=matchedCommand.group(4)))
        return

    # Catch other MMU3 lines not caught by regex
    # ATTENTION. Some errors spam one of these lines, so deduplicate them here. It's possible some
    # error may not print one of these lines, but I haven't found one
    elif (
      (MMU3Codes.SAVING_PARKING in line or MMU3Codes.COOLDOWN_PENDING in line) and
      self.mmu[MmuKeys.STATE] != MmuStates.ATTENTION
    ):
      self._fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.ATTENTION))
    # PAUSED_USER is caught in the MMU2 section early on in this function, but we need to recover
    # from it if the MMU's response is the same as LAST_LINE
    elif self.mmu[MmuKeys.STATE] == MmuStates.PAUSED_USER and MMU3Codes.LCD_CHANGED in line:
      # If detected, blank out LAST_LINE. The next mmu response in the log will trigger again and
      # change the state away from PAUSED_USER
      self.mmu[MmuKeys.LAST_LINE] = ""

    return

  # Listen for MMU events and update the nav to reflect it
  def gcode_received_hook(self, comm, line, *args, **kwargs):
    # Another Firmware check in case the actual one fails.
    if self.mmu[MmuKeys.PRUSA_VERSION] is None and line.startswith("FIRMWARE_NAME"):
      self._log("gcode_received_hook FIRMWARE_NAME: {}".format(line), debug=True)
      self._process_firmware(line)
      return line

    # Until we have a version there's no point in trying to parse
    if self.mmu[MmuKeys.PRUSA_VERSION] is None:
      return line

    # MK3.5/3.9/4
    if (
      self.mmu[MmuKeys.PRUSA_VERSION] != PrusaProfile.MK3 and
      self.mmu[MmuKeys.PRUSA_VERSION] is not None
    ):
      self.mk4_gcode_received(line)
      return line

    # MK3
    self.mk3_gcode_received(line)
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
      x = search(TOOL_REGEX, cmd)
      tool = x.group(1)

      # If the tool does not match the current tool then we're about to get an unload message from
      # the printer so set the previous tool's value before we replace tool.
      if self.mmu[MmuKeys.TOOL] != tool:
        self.mmu[MmuKeys.PREV_TOOL] = self.mmu[MmuKeys.TOOL]

      # Store the tool value on the tool. We're about to get a loading call.
      self.mmu[MmuKeys.TOOL] = tool
      self._log("gcode_sent_hook Tool:{} Prev:{}".format(tool, self.mmu[MmuKeys.PREV_TOOL]),
                debug=True)
    except:
      pass

    return

  # ======== EventHandlerPlugin ========

  def _fire_event(self, key, payload=None):
    if key != PluginEventKeys.MMU_CHANGE:
      self._event_bus.fire(key, payload=payload)

    newPayload = self.mmu.copy()
    if payload is not None:
      newPayload.update(payload)

    # Dedupe events
    if (
      self.mmu[MmuKeys.STATE] == newPayload[MmuKeys.STATE] and
      self.mmu[MmuKeys.TOOL] == newPayload[MmuKeys.TOOL] and
      self.mmu[MmuKeys.PREV_TOOL] == newPayload[MmuKeys.PREV_TOOL] and
      self.mmu[MmuKeys.RESPONSE] == newPayload[MmuKeys.RESPONSE] and
      self.mmu[MmuKeys.RESPONSE_DATA] == newPayload[MmuKeys.RESPONSE_DATA] and
      self.mmu[MmuKeys.PRUSA_VERSION] == newPayload[MmuKeys.PRUSA_VERSION]
    ):
      return newPayload
    
    self.mmu = newPayload

    # Steps are taken in gcode_received_hook to reduce the spamminess of events. Proper
    # deduplication happens in on_event
    # self._log("_fire_event {} with".format(key), obj=payload, debug=True)
    self._event_bus.fire(key, payload=newPayload)

    return newPayload

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
    #   self._log("on_event {} with".format(event, obj=payload, debug=True))
    #   return

    # Fired any time we detect a command that would update something about the MMU
    if event == PluginEventKeys.MMU_CHANGE:
      self._log("on_event {} with".format(event), obj=payload, debug=True)
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
    
    if event == Events.PRINT_STARTED:
      self._log("on_event {}".format(event), debug=True)
      # If we start a print and version is empty then set it to MK3
      if self.mmu[MmuKeys.PRUSA_VERSION] is None:
        self.mmu[MmuKeys.PRUSA_VERSION] = PrusaProfile.MK3

      if (
        self.mmu[MmuKeys.PRUSA_VERSION] != PrusaProfile.MK3 and
        self.config[SettingsKeys.ENABLE_PROMPT]
      ):
        self._show_prompt()
        if not self._printer.set_job_on_hold(True):
          self._log("PAUSE FAILED?", debug=True)
        return

    # Handle disconnected event to set the mmu to Not Found (no printer...)
    if event == Events.DISCONNECTED:
      self._log("on_event {}".format(event), debug=True)
      self._disable_mk4_remap()
      self._fire_event(PluginEventKeys.MMU_CHANGE, DEFAULT_MMU_STATE.copy())
      return

    # Handle terminal states when printer is no longer printing to reset the MMU
    if (
      event == Events.PRINT_DONE or
      event == Events.PRINT_CANCELLED or
      (event == Events.PRINT_FAILED and self.mmu[MmuKeys.STATE] != MmuStates.ATTENTION)
    ):
      self._log("on_event {}".format(event), debug=True)
      newMmu = DEFAULT_MMU_STATE.copy()
      newMmu[MmuKeys.STATE] = MmuStates.OK
      newMmu[MmuKeys.PRUSA_VERSION] = self.mmu[MmuKeys.PRUSA_VERSION]
      self._disable_mk4_remap()
      self._fire_event(PluginEventKeys.MMU_CHANGE, newMmu)
      return

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
    # ensure timeout is correct
    try:
      if SettingsKeys.TIMEOUT not in data:
        data[SettingsKeys.TIMEOUT] = self._settings.get_int([SettingsKeys.TIMEOUT])
      data[SettingsKeys.TIMEOUT] = int(data[SettingsKeys.TIMEOUT])

      if data[SettingsKeys.TIMEOUT] < 1:
        data[SettingsKeys.TIMEOUT] = DEFAULT_TIMEOUT
    except:
      data[SettingsKeys.TIMEOUT] = DEFAULT_TIMEOUT

    self._log("on_settings_save", debug=True)

    # save settings
    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
    self._refresh_config()

  def _refresh_config(self):
    self.config[SettingsKeys.DEBUG] = self._settings.get_boolean([SettingsKeys.DEBUG])
    self.config[SettingsKeys.SIMPLE_DISPLAY_MODE] = self._settings.get_boolean([
      SettingsKeys.SIMPLE_DISPLAY_MODE])
    self.config[SettingsKeys.ADVANCED_DISPLAY_MODE] = self._settings.get_boolean([
      SettingsKeys.ADVANCED_DISPLAY_MODE])

    self.config[SettingsKeys.TIMEOUT] = self._settings.get_int([SettingsKeys.TIMEOUT])
    self.config[SettingsKeys.USE_DEFAULT_FILAMENT] = self._settings.get_boolean([
      SettingsKeys.USE_DEFAULT_FILAMENT])
    self.config[SettingsKeys.DEFAULT_FILAMENT] = self._settings.get_int([
      SettingsKeys.DEFAULT_FILAMENT])

    self.config[SettingsKeys.DISPLAY_ACTIVE_FILAMENT] = self._settings.get_boolean([
      SettingsKeys.DISPLAY_ACTIVE_FILAMENT])
    self.config[SettingsKeys.FILAMENT_SOURCE] = self._settings.get([SettingsKeys.FILAMENT_SOURCE])
    self.config[SettingsKeys.FILAMENT_SOURCES] = self._settings.get([SettingsKeys.FILAMENT_SOURCES])
    self.config[SettingsKeys.USE_FILAMENT_MAP] = self._settings.get_boolean([
      SettingsKeys.USE_FILAMENT_MAP])
    self.config[SettingsKeys.FILAMENT_MAP] = self._settings.get([SettingsKeys.FILAMENT_MAP])
    self.config[SettingsKeys.ENABLE_PROMPT] = self._settings.get_boolean([
      SettingsKeys.ENABLE_PROMPT])

    # handle overwriting the prusa version but don't rewrite if it's blank.
    self.config[SettingsKeys.PRUSA_VERSION] = self._settings.get([SettingsKeys.PRUSA_VERSION])
    self._process_firmware(self.config[SettingsKeys.PRUSA_VERSION].replace("_", "."), True)

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
