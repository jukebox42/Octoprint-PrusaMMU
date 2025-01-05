from re import search

from octoprint_prusammu.common.Mmu import MmuStates, MmuKeys, MMU3Codes, \
  MMU3RequestCodes, MMU3ResponseCodes, MMU3MK4Commands

def mk4_gcode_received(mmu, lastMmuAction, line):
  # The MK4 is less verbose. To try and fill that gap we're faking the response and responseData
  # to try and match the information we'd expect to get. Some day I hope prusa gives us back
  # the data we had before.

  ret = dict(
    action=None,
    lastAction=None
  )

  # Dedupe
  if "MMU2:" in line:
    if mmu[MmuKeys.LAST_LINE] == line:
      return ret
    ret[MmuKeys.LAST_LINE] = line

  # Paused
  if MMU3MK4Commands.PAUSED_USER in line:
    ret["lastAction"] = MmuStates.PAUSED_USER
    # The printer will spam pause messages, so ignore them if we're already paused
    if mmu[MmuKeys.STATE] == MmuStates.PAUSED_USER:
      return ret
    # The printer will send pause messages directly after an attention, and attention is more
    # important, so ignore them
    elif mmu[MmuKeys.STATE] == MmuStates.ATTENTION:
      return ret
    
    return ret.update({
      "action": "update",
      "state": MmuStates.PAUSED_USER,
      "response": MMU3ResponseCodes.ERROR,
      "responseData": "c",
    })

  # Errors
  if MMU3MK4Commands.ERROR in line:
    # TODO: This is a more generic error. we might be able to get something out of the bytes sent.
    return ret.update({
      "action": "update",
      "state": MmuStates.ATTENTION,
      "response": MMU3ResponseCodes.ERROR,
      "responseData": "c",
    })

  if MMU3MK4Commands.ERROR_FILAMENT in line:
    return ret.update({
      "action": "update",
      "state": MmuStates.ATTENTION,
      "response": MMU3ResponseCodes.ERROR,
      "responseData": "f",
    })

  if MMU3MK4Commands.ERROR_INTERNAL in line:
    return ret.update({
      "action": "update",
      "state": MmuStates.ATTENTION,
      "response": MMU3ResponseCodes.ERROR,
      "responseData": "d",
    })

  if MMU3MK4Commands.ERROR_TMC in line:
    return ret.update({
      "action": "update",
      "state": MmuStates.ATTENTION,
      "response": MMU3ResponseCodes.ERROR,
      "responseData": "e",
    })

  # Loading
  if MMU3MK4Commands.LOADING_FINDA in line:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.LOADING,
      "tool": mmu[MmuKeys.TOOL],
      "state": MmuStates.LOADING,
      "response": MMU3ResponseCodes.PROCESSING,
      "responseData": "5",
    })

  if MMU3MK4Commands.LOADING_EXTRUDER in line:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.LOADING,
      "tool": mmu[MmuKeys.TOOL],
      "state": MmuStates.LOADING,
      "response": MMU3ResponseCodes.PROCESSING,
      "responseData": "6",
    })

  if MMU3MK4Commands.LOADING_FSENSOR in line:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.LOADING,
      "tool": mmu[MmuKeys.TOOL],
      "state": MmuStates.LOADING,
      "response": MMU3ResponseCodes.PROCESSING,
      "responseData": "7",
    })

  # Loaded, clear previous tool
  if  MMU3MK4Commands.ACTION_DONE in line and lastMmuAction == MmuStates.LOADING:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.LOADED,
      "tool": mmu[MmuKeys.TOOL],
      "previousTool": "",
      "state": MmuStates.LOADED,
      "response": MMU3ResponseCodes.FINISHED,
      "responseData": "2",
    })

  # Unloading (changing tool)
  if MMU3MK4Commands.UNLOADING in line:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.UNLOADING,
      "state": MmuStates.UNLOADING,
      "response": MMU3ResponseCodes.PROCESSING,
      "responseData": "3",
    })

  # Unloading Final (print done)
  if MMU3MK4Commands.UNLOADING_FINAL in line:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.UNLOADING_FINAL,
      "state": MmuStates.UNLOADING,
      "response": MMU3ResponseCodes.PROCESSING,
      "responseData": "3",
    })

  # Unloaded Final
  if MMU3MK4Commands.ACTION_DONE in line and lastMmuAction == MmuStates.UNLOADING_FINAL:
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.OK,
      "state": MmuStates.OK,
      "response": MMU3ResponseCodes.FINISHED,
      "responseData": "2",
    })

  # Starting
  if search(MMU3MK4Commands.START_MATCH, line):
    # We fire them back to back because we no longer get a ready message from the MMU
    return ret.update({
      "action": "update",
      "lastAction": MmuStates.OK,
      "state": MmuStates.STARTING,
      "response": MMU3ResponseCodes.FINISHED,
      "responseData": "0",
    })

  return ret

def mk3_gcode_received(mmu, line):
  ret = dict(
    action=None,
  )

  # MMU2 3.0.0
  # https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_progress_converter.cpp#L8
  # https://github.com/prusa3d/Prusa-Firmware/blob/d84e3a9cf31963b9378b9cf39cd3dd4c948a05d6/Firmware/mmu2_protocol_logic.cpp
  # General REGEX to catch all important MMU commands
  if search(MMU3Codes.GENERAL_MATCH, line):
    # If this line is the same as the previously seen one, ignore it and return immediately,
    # otherwise it's new, so continue
    if mmu[MmuKeys.LAST_LINE] == line:
      return ret
    ret[MmuKeys.LAST_LINE] = line

    # Search the line. This creates 4 matched groups. 
    # Group 1 is a single letter request code. Group 2 is the request data in hexidecimal
    # Group 3 is a single letter response code. Group 4 is the response data in hexidecimal.
    # Warning, it may not exist!
    matchedCommand = search(MMU3Codes.GROUP_MATCH, line)
    # _log("Matched Line Info: Line: " + line + " Groups: " + matchedCommand.group(1) + "," +
    #           matchedCommand.group(2) + "," + matchedCommand.group(3) + "," +
    #           matchedCommand.group(4), debug=True)

    # If we're already at attention, and the new MMU response has an error, stay at attention and
    # add the error code, then stop checking. Otherwise the new MMU response shows that the
    # ATTENTION has cleared, so continue and get the new state.
    if (
      mmu[MmuKeys.STATE] == MmuStates.ATTENTION and
      matchedCommand.group(3) == MMU3ResponseCodes.ERROR
    ):
      return ret.update({
        "action": "update",
        "state": MmuStates.ATTENTION,
        "response": matchedCommand.group(3),
        "responseData": matchedCommand.group(4),
      })

    # Load filament to nozzle
    if matchedCommand.group(1) == MMU3RequestCodes.TOOL:
      # Loading Finished, Printer is now loaded. Clear previous tool
      if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
        return ret.update({
          "action": "update",
          "state": MmuStates.LOADED,
          "previousTool": "",
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
      # Still Loading
      else:
        return ret.update({
          "action": "update",
          "state": MmuStates.LOADING,
          "tool": matchedCommand.group(2),
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
    # Preload filament to mmu
    elif matchedCommand.group(1) == MMU3RequestCodes.LOAD:
      # Preload Finished, Printer is now idle
      if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
        return ret.update({
          "action": "update",
          "state": MmuStates.OK,
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
      # Preload in progress
      else:
        return ret.update({
          "action": "update",
          "state": MmuStates.LOADING_MMU,
          "tool": matchedCommand.group(2),
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
    # Unload Filament from Nozzle NOTE: Doesn't give us any tool info, so rely on T# commands to
    # give us current and previous tool info
    elif matchedCommand.group(1) == MMU3RequestCodes.UNLOAD:
      # Unload Finished, Printer is now idle
      if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
        return ret.update({
          "action": "update",
          "state": MmuStates.OK,
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
      # Unload in progress
      else:
        return ret.update({
          "action": "update",
          "state": MmuStates.UNLOADING,
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
    # Printer Reset, Shows up after power on
    elif matchedCommand.group(1) == MMU3RequestCodes.RESET:
      return ret.update({
        "action": "update",
        "state": MmuStates.OK,
        "response": matchedCommand.group(3),
        "responseData": matchedCommand.group(4),
      })
    # Cut Filament
    elif matchedCommand.group(1) == MMU3RequestCodes.CUT:
      # Cutting finished, Printer is now idle
      if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
        return ret.update({
          "action": "update",
          "state": MmuStates.OK,
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
      # Cutting in progress
      else:
        return ret.update({
          "action": "update",
          "state": MmuStates.CUTTING,
          "tool": matchedCommand.group(2),
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
    # Eject Filament
    elif matchedCommand.group(1) == MMU3RequestCodes.EJECT:
      # Ejecting finished, Printer is now idle
      if matchedCommand.group(3) == MMU3ResponseCodes.FINISHED:
        return ret.update({
          "action": "update",
          "state": MmuStates.OK,
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })
      # Ejecting in progress
      else:
        return ret.update({
          "action": "update",
          "state": MmuStates.EJECTING,
          "tool": matchedCommand.group(2),
          "response": matchedCommand.group(3),
          "responseData": matchedCommand.group(4),
        })

  # Catch other MMU3 lines not caught by regex
  # ATTENTION. Some errors spam one of these lines, so deduplicate them here. It's possible some
  # error may not print one of these lines, but I haven't found one
  elif (
    (MMU3Codes.SAVING_PARKING in line or MMU3Codes.COOLDOWN_PENDING in line) and
    mmu[MmuKeys.STATE] != MmuStates.ATTENTION
  ):
    return ret.update({
      "action": "update",
      "state": MmuStates.ATTENTION,
    })
    _fire_event(PluginEventKeys.MMU_CHANGE, dict(state=MmuStates.ATTENTION))
  # PAUSED_USER is caught in the MMU2 section early on in this function, but we need to recover
  # from it if the MMU's response is the same as LAST_LINE
  elif mmu[MmuKeys.STATE] == MmuStates.PAUSED_USER and MMU3Codes.LCD_CHANGED in line:
    # If detected, blank out LAST_LINE. The next mmu response in the log will trigger again and
    # change the state away from PAUSED_USER
    ret[MmuKeys.LAST_LINE] = line

  return ret