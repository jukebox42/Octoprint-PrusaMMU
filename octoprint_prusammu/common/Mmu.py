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
  LOADING_MMU="LOADING_MMU"
  CUTTING="CUTTING"
  EJECTING="EJECTING"


class MmuKeys():
  STATE="state"
  LAST_LINE="lastLine"
  TOOL="tool"
  PREV_TOOL="previousTool"
  RESPONSE="response"
  RESPONSE_DATA="responseData"

DEFAULT_MMU_STATE = dict(
  state=MmuStates.NOT_FOUND,
  lastLine="",
  tool="",
  previousTool="",
  response="",
  responseData="",
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
# The 3.0.0 software brings improved logging for the MMU. A response from the MMU would look like:
# MMU2:<L0 P5
# Which represents:
# MMU2:<(request)(request data) (response)(response data)
# Using this we can determine:
# The MMU is (L)oading to MMU filament (0), and it is currently in (P)rogress with code (5), which translates to "Feeding to FINDA"
class MMU3Codes():
  # General check for MMU commands we care about. MMU2:< ensures that only messages FROM the MMU are detected. [TLUXKE] Matches a single character, only for request codes we care about
  GENERAL_MATCH="MMU2:<[TLUXKE]"
  # This regex match contains 4 groups. 
  # MMU2:< ensures that only messages FROM the MMU are detected. 
  # Group 1 is the single letter request code that the MMU is responding to. Only codes that we care about are checked for: T,L,U,X,K,E
  # Group 2 is the request code data. It's usually 0 unless the code involves filament, then this contains the filament number (0-4)
  # Group 3 is the response code. It shows that current status of the command the MMU is performing. Possible responses: P,E,F,A,R,B
  # Group 4 is the response data. It contains extra info in hex depending on the response code. The amount of hex data can range, or even be empty! Check MMU3ResponseCodes below for more info
  GROUP_MATCH="MMU2:<([TLUXKE])(.*) ([PEFARB])(.*)\*"
  # These two lines can be used to tell that the MMU is stopped, waiting for user
  SAVING_PARKING="MMU2:Saving and parking"
  COOLDOWN_PENDING="MMU2:Heater cooldown pending"
  # This is our only sign that the user is done with a PAUSED_USER event.
  LCD_CHANGED="LCD status changed"

# These request codes are commands sent by the printer to the MMU, but the MMU responds with the same code during the Q - Query request, and 
# when responding to the request, so we can just listen for the MMU's responses to find out which action it's currently doing.
# Codes are taken from here:
# https://github.com/prusa3d/Prusa-Firmware/blob/MK3/Firmware/mmu2_protocol.h
class MMU3RequestCodes():
  # T -            Tool - Tells the MMU to load a filament from the MMU to the nozzle. Followed by the filament number 0-4. To test, use Gcode Tx, or M701 P#
  TOOL="T"
  # L -            Load - Tells the MMU to preload the filament to the MMU. Followed by the filament number 0-4. To test, use M704 P#
  LOAD="L"
  # U -          Unload - Tells the MMU to unload the current filament. Does NOT contain the filament number, it seems to always be 0. To test, use M702
  UNLOAD="U"
  # X -           Reset - Tells the MMU to reset itself. The MMU also responds to Query with this when it first boots. Seems to always be 0. To test, use M709 X0
  RESET="X"
  # K -             Cut - Tells the MMU to cut the filament. Followed by the filament number 0-4. To test, use M706 P#
  CUT="K"
  # E -           Eject - Tells the MMU to eject the filament (out of the front of the MMU). Followed by the filament number 0-4. To test use M705 P#
  EJECT="E"
  # Unused request codes. Most of these have no use to us:
  # Q -           Query - Tells the MMU to respond with whatever request it's working on, and it's progress. The Printer sends this, but the MMU never seems to respond with this code, it replies with the working request instead
  # M -            Mode - Theoretically used when the printer tells the MMU to change betweeen normal and stealth mode
  # P -           Finda - Tells the MMU to send the Finda state
  # S -         Version - Tells the MMU to send firmware version info. The printer sends these when the MMU is first connected. S0 = Major version. S1 = Minor S2 = Revision. S3 = Build number
  # B -          Button - Tells the MMU to trigger a function, as if a button were pressed. B0=nothing. B1=Retry. B2=Continue. B3=ResetMMU. B4=Unload. B5=Load. B6=Eject. B7=Tune. B8=StopPrint. B9=DisableMMU
  #                       Unfortunately there doesn't seem to be a way to trigger these via gcode, or it might be possible to resolve some errors remotely.
  # W -           Write - Tells the MMU to write to a register. Check https://help.prusa3d.com/article/registers-mmu-mmu3_511780 for register info. You can trigger this via M708 A[ADDRESS] X[VALUE]
  # F -   Filament Type - Theoretically tells the MMU to change the filament type. Apparently used for flex filaments and PVA. Maybe related to M403
  # f - Filament Sensor - Tells the MMU the status of the Filament Sensor. The Printer sends this constantly during Tool/Unload commands.
  # H -            Home - Theoretically tells the MMU to home itself. I've never seen this sent from the printer, and there doesn't seem to be a gcode command for it. The MMU usually homes itself when needed without sending a code
  # R -            Read - Tells the MMU to read from a register. Lots of these during the normal 1 second MMU status checks. Check https://help.prusa3d.com/article/registers-mmu-mmu3_511780 for register info. You can trigger this via M707 A[ADDRESS]

# These response codes follow a request code, and display the status of the request
# The amount of response data can vary, depending on the request code
class MMU3ResponseCodes():
  # P - Processing - The MMU is still working on the request. The response data is a one or two digit hex code for the progress message
  PROCESSING="P"
  # E -      Error - The MMU had an error while working on the request. The response data is a 4 digit hex code for the error message
  ERROR="E"
  # F -   Finished - The MMU is done with the request. The response data seems to always be 0
  FINISHED="F"
  # A -   Accepted - The MMU has accepted the request. The response data varies depending on the command. I'll list the ones that I've figured out
  #                  For T,L,U,K,E,B,W,f, there is no value to return, so the response data is empty!
  #                  For R, the response data is an arbitrarially large amount of hex data that is the output of the address read.
  #                  For S, the response data is an arbitrarially large amount of hex data representing the version info. Works the same way as R
  #                  Unknown response types: M,P,F,H
  ACCEPTED="A"
  # R -   Rejected - The MMU has rejected the request, because it is busy. The easiest way to simulate this it to press a button on the MMU, then send a conflicting Gcode action. 
  #                  The printer spams the next command until the MMU eventually takes it
  REJECTED="R"
  # B -     Button - Theoretically the MMU sends the pressed button to the printer for processing. I've never seen it in any log outputs
  BUTTON="B"