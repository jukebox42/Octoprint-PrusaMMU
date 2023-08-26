# coding=utf-8
from __future__ import absolute_import


class MmuStates():
  NOT_FOUND="NOT_FOUND"
  STARTING="STARTING"
  OK="OK"
  LOADED="LOADED"
  UNLOADING="UNLOADING"
  LOADING="LOADING"
  PAUSED_USER="PAUSED_USER"
  ATTENTION="ATTENTION"


class MmuKeys():
  STATE="state"
  TOOL="tool"
  PREV_TOOL="previousTool"

DEFAULT_MMU_STATE = dict(
  state=MmuStates.NOT_FOUND,
  tool="",
  previousTool="",
)

class MMU2Commands():
  PAUSED_USER="paused for user"
  START="MMU => 'start'"
  NOT_RESPONDING="MMU not responding"
  ENABLED="MMU - ENABLED"
  STARTS_RESPONDING="MMU starts responding"
  LOADING="MMU can_load"
  UNLOADING_DONE="Unloading finished"
  LOADED="OO succeeded"

# https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_protocol.h
# The 3.0.0 software brings improved logging for the MMU. A command breakdown would look like:
# MMU2:<L0 F0
# Which represents:
# MMU2:(response) (command)(tool) (action)(tries)
# Using this we can determine:
# The MMU (F)inished (L)oading Tool 0, and it only took 0(one) tries.
class MMU3Codes():
  # Tool
  # TODO: What's the different between Tool Finished and Load Finished? I don't see Load Finished in multi-color prints.
  TOOL_START="MMU[23]:<T[0-4] A"
  TOOL_PROCESSING="MMU[23]:<T[0-4] P"
  TOOL_FINISHED="MMU[23]:<T[0-4] F0"
  # Load
  LOAD_START="MMU[23]:<L[0-4] A"
  LOAD_PROCESSING="MMU[23]:<:L[0-4] P"
  LOAD_FINISHED="MMU[23]:<L[0-4] F"
  # Unload
  UNLOAD_START="MMU[23]:<U[0-4] A"
  UNLOAD_PROCESSING="MMU[23]:<U[0-4] P"
  UNLOAD_FINISHED="MMU[23]:<U[0-4] F"

class MMU3Commands():
  INIT="Cap:PRUSA_MMU2:1"
  ERROR="MMU2:Command Error"
  BUTTON="MMU2:Button"
  READ="MMU2:<"
  # Not technically an MMU command but tells us the last action was successful probably.
  RESET_RETRY="ResetRetryAttempts"
  # https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_progress_converter.cpp#L8
  OK="MMU2:OK"
  ENGAGE_IDLER="MMU2:Engaging idler"
  DISENGAGE_IDLER="MMU2:Disengaging idler"
  UNLOAD_FINDA="MMU2:Unloading to FINDA"
  UNLOAD_PULLEY="MMU2:Unloading to pulley"
  FEED_FINDA="MMU2:Feeding to FINDA"
  FEED_EXTRUDER="MMU2:Feeding to extruder"
  FEED_NOZZLE="MMU2:Feeding to nozzle"
  AVOID_GRIND="MMU2:Avoiding grind"
  WAIT_USER="MMU2:ERR Wait for User"
  ERR_INTERNAL="MMU2:ERR Internal"
  ERR_HELP_FIL="MMU2:ERR Help filament"
  ERR_TMC="MMU2:ERR TMC failed"
  SELECT_SLOT="MMU2:Selecting fil. slot"
  PREPARE_BLADE="MMU2:Preparing blade"
  PUSH_FILAMENT="MMU2:Pushing filament"
  PERFORM_CUT="MMU2:Performing cut"
  RETURN_SELECTOR="MMU2:Returning selector"
  PARK_SELECTOR="MMU2:Parking selector"
  EJECT_FILAMENT="MMU2:Ejecting filament"
  RETRACT_FINDA="MMU2:Retract from FINDA"
  HOMING="MMU2:Homing"
  MOVING_SELECTOR="MMU2:Moving selector"
  FEED_FSENSOR="MMU2:Feeding to FSensor"