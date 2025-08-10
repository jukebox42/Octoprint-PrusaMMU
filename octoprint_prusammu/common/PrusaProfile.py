# coding=utf-8
from __future__ import absolute_import


# The command sent on connection to tell us what type of printer we have
class MachineType():
  MK3="MK3S"
  MK3_5="MK3.5"
  MK3_9="MK3.9"
  MK4="MK4"
  CORE="COREONE"

  # Print Profile (or the profile of the printer in the gcode)
class PrusaProfile():
  MK3="MK3"
  MK3_5="MK3_5"
  MK3_9="MK3_9"
  MK4="MK4"
  CORE="COREONE"

# Given a machine type it returns the profile type
def detect_connection_profile(machine_type):
  if MachineType.MK3_5 in machine_type:
    return PrusaProfile.MK3_5
  if MachineType.MK3_9 in machine_type:
    return PrusaProfile.MK3_9
  if MachineType.MK4 in machine_type:
    return PrusaProfile.MK4
  if MachineType.CORE in machine_type:
    return PrusaProfile.CORE
  # Fallback to the MK3
  return PrusaProfile.MK3