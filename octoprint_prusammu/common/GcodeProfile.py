# coding=utf-8
from __future__ import absolute_import
from octoprint_prusammu.common.PrusaProfile import PrusaProfile

# TODO: Rename this, you can do better.


# Used to detect if we're in multi mode or single mode. (only for 3.5/3.9/4)
DETECT_MMU = "M862.6 P \"MMU3\""

# Each of these printers have their own pause line
def is_pause_line(cmd, profile):
  if profile == PrusaProfile.MK3 and cmd.startswith("M109 S"):
    return True
  elif profile == PrusaProfile.MK3_5 and cmd.startswith("M109 S"):
    return True
  elif profile == PrusaProfile.MK3_9 and cmd.startswith("M569 S0 E"):
    return True
  elif profile == PrusaProfile.MK4 and cmd.startswith("M569 S0 E"):
    return True
  return False

# When using single mode, this appends the extra functions needed to support tool changing.
# terrified to test these to be honest.
def get_additional_lines(profile):
  if profile == PrusaProfile.MK3:
    return []
  elif profile == PrusaProfile.MK3_5:
    return [
      ("G1 E60 F1000",),
    ]
  elif profile == PrusaProfile.MK3_9:
    return [
      ("G1 E17 F1000",),
    ]
  elif profile == PrusaProfile.MK4:
    return [
      ("G1 E17 F1000",),
    ]
  return []