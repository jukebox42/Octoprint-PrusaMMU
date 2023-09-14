/**
 * Given a progress code it returns a string to be displayed as a message in the navbar
 * 
 * @param {string} code - The progress code hexidecimal value as a string
 * @returns string
 */
const getMmuProgress = (code) => {
  try {
    if (!code) {
      return MMU2MmuProgressStrings["UNKNOWN"];
    }

    if (MMU2MmuProgressStrings[code]) {
      return MMU2MmuProgressStrings[code];
    }
  } catch (e) { console.error(e); }

  return MMU2MmuProgressStrings["UNKNOWN"];
};
/**
 * The hex number determines the message. The below messages come from:
 * https://github.com/prusa3d/Prusa-Firmware/blob/MK3/Firmware/mmu2_progress_converter.cpp
 */
const MMU2MmuProgressStrings = {
  "0": "OK",
  "1": "Engaging idler",
  "2": "Disengaging idler",
  "3": "Unloading to FINDA",
  "4": "Unloading to pulley",
  "5": "Feeding to FINDA",
  "6": "Feeding to extruder",
  "7": "Feeding to nozzle",
  "8": "Avoiding grind",
  "9": "Finishing movements",
  "a": "Disengaging idler",
  "b": "Engaging idler",
  "c": "ERR Wait for User",
  "d": "ERR Internal",
  "e": "ERR Help filament",
  "f": "ERR TMC failed",
  "10": "Unloading filament",
  "11": "Loading filament",
  "12": "Selecting fil. slot",
  "13": "Preparing blade",
  "14": "Pushing filament",
  "15": "Performing cut",
  "16": "Returning selector",
  "17": "Parking selector",
  "18": "Ejecting filament",
  "19": "Retract from FINDA",
  "1a": "Homing",
  "1b": "Moving selector",
  "1c": "Feeding to FSensor",
  UNKNOWN: "UNKNOWN",
};
