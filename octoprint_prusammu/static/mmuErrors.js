/**
 * Given an error code it finds the corresponding error in the MMU2MmuErrorStrings map.
 * TODO: This will lie to owners not running 3.0.0 as it'll always return an UNKNOWN for them.
 * 
 * @param {string} code - The string identifier for the error. Will be "E" followed by a 4 digit hex code.
 * @returns 
 */
const getMmuError = (code) => {
  try {
    if (!code) {
      return MMU2MmuErrorStrings["UNKNOWN"];
    }

    if (MMU2MmuErrorStrings[code]) {
      return MMU2MmuErrorStrings[code];
    }
  } catch (e) { console.error(e); }

  return MMU2MmuErrorStrings["UNKNOWN"];
};

/**
 * The map below's keys come from:
 * https://github.com/prusa3d/Prusa-Firmware/blob/4c531630686b4918ae442a27dce67c01f351c757/Firmware/mmu2/error_codes.h
 * mapped by 
 * https://github.com/prusa3d/Prusa-Firmware/blob/MK3/Firmware/mmu2_error_converter.cpp
 * to
 * https://raw.githubusercontent.com/prusa3d/Prusa-Error-Codes/master/04_MMU/error-codes.yaml
 * 
 * Missing codes or ones I couldn't figure out how to map start with an X.
 */
const MMU2MmuErrorStrings = {
  // MECHANICAL
  E8001: {
    code:"04101",
    title:"FINDA DIDNT TRIGGER",
    text:"FINDA didn't trigger while loading the filament. Ensure the filament can move and FINDA works.",
    id:"FINDA_DIDNT_TRIGGER",
  },

  E8002: {
    code:"04102",
    title:"FINDA FILAM. STUCK",
    text:"FINDA didn't switch off while unloading filament. Try unloading manually. Ensure filament can move and FINDA works.",
    id:"FINDA_FILAMENT_STUCK",
  },

  E8003 : {
    code:"04103",
    title:"FSENSOR DIDNT TRIGG.",
    text:"Filament sensor didn't trigger while loading the filament. Ensure the sensor is calibrated and the filament reached it.",
    id:"FSENSOR_DIDNT_TRIGGER",
  },

  E8004: {
    code:"04104",
    title:"FSENSOR FIL. STUCK",
    text:"Filament sensor didn't switch off while unloading filament. Ensure filament can move and the sensor works.",
    id:"FSENSOR_FILAMENT_STUCK",
  },

  E8047: {
    code:"04105",
    title:"PULLEY CANNOT MOVE",
    text:"Pulley motor stalled. Ensure the pulley can move and check the wiring.",
    id:"PULLEY_CANNOT_MOVE",
  },

  // This second E8xxx code causes the same error to be output
  E804b: {
    code:"04105",
    title:"PULLEY CANNOT MOVE",
    text:"Pulley motor stalled. Ensure the pulley can move and check the wiring.",
    id:"PULLEY_CANNOT_MOVE",
  },

  E8009: {
    code:"04106",
    title:"FSENSOR TOO EARLY",
    text:"Filament sensor triggered too early while loading to extruder. Check there isn't anything stuck in PTFE tube. Check that sensor reads properly.",
    id:"FSENSOR_TOO_EARLY",
  },

  E800a: {
    code:"04107",
    title:"INSPECT FINDA",
    text:"Selector can't move due to FINDA detecting a filament. Make sure no filament is in Selector and FINDA works properly.",
    id:"INSPECT_FINDA",
  },

  E802a: {
    code:"04108",
    title:"LOAD TO EXTR. FAILED",
    text:"Loading to extruder failed. Inspect the filament tip shape. Refine the sensor calibration, if needed.",
    id:"LOAD_TO_EXTRUDER_FAILED",
  },

  E8087: {
    code:"04115",
    title:"SELECTOR CANNOT HOME",
    text:"The Selector cannot home properly. Check for anything blocking its movement.",
    id:"SELECTOR_CANNOT_HOME",
  },

  E808b: {
    code:"04116",
    title:"SELECTOR CANNOT MOVE",
    text:"The Selector cannot move. Check for anything blocking its movement. Check if the wiring is correct.",
    id:"SELECTOR_CANNOT_MOVE",
  },

  E8107: {
    code:"04125",
    title:"IDLER CANNOT HOME",
    text:"The Idler cannot home properly. Check for anything blocking its movement.",
    id:"IDLER_CANNOT_HOME",
  },

  E810b: {
    code:"04126",
    title:"IDLER CANNOT MOVE",
    text:"The Idler cannot move properly. Check for anything blocking its movement. Check if the wiring is correct.",
    id:"IDLER_CANNOT_MOVE",
  },

  // TEMPERATURE    xx2xx   // Temperature measurement

  EA000: {
    code:"04201",
    title:"WARNING TMC TOO HOT",
    text:"TMC driver for the Pulley motor is almost overheating. Make sure there is sufficient airflow near the MMU board.",
    text_short:"More details online.",
    id:"WARNING_TMC_PULLEY_TOO_HOT",
  },

  /*EA000: {
    code:"04211",
    title:"WARNING TMC TOO HOT",
    text:"TMC driver for the Selector motor is almost overheating. Make sure there is sufficient airflow near the MMU board.",
    text_short:"More details online.",
    id:"WARNING_TMC_SELECTOR_TOO_HOT",
  },

  EA000: {
    code:"04221",
    title:"WARNING TMC TOO HOT",
    text:"TMC driver for the Idler motor is almost overheating. Make sure there is sufficient airflow near the MMU board.",
    text_short:"More details online.",
    id:"WARNING_TMC_IDLER_TOO_HOT",
  },*/

  EC000: {
    code:"04202",
    title:"TMC OVERHEAT ERROR",
    text:"TMC driver for the Pulley motor is overheated. Cool down the MMU board and reset MMU.",
    text_short:"More details online.",
    id:"TMC_PULLEY_OVERHEAT_ERROR",
  },

  /*EC000: {
    code:"04212",
    title:"TMC OVERHEAT ERROR",
    text:"TMC driver for the Selector motor is overheated. Cool down the MMU board and reset MMU.",
    text_short:"More details online.",
    id:"TMC_SELECTOR_OVERHEAT_ERROR",
  },

  EC000: {
    code:"04222",
    title:"TMC OVERHEAT ERROR",
    text:"TMC driver for the Idler motor is overheated. Cool down the MMU board and reset MMU.",
    text_short:"More details online.",
    id:"TMC_IDLER_OVERHEAT_ERROR",
  },*/

  // ELECTRICAL     xx3xx

  E8200: {
    code:"04301",
    title:"TMC DRIVER ERROR",
    text:"TMC driver for the Pulley motor is not responding. Try resetting the MMU. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_PULLEY_DRIVER_ERROR",
  },

  /*E8200: {
    code:"04311",
    title:"TMC DRIVER ERROR",
    text:"TMC driver for the Selector motor is not responding. Try resetting the MMU. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_SELECTOR_DRIVER_ERROR",
  },

  E8200: {
    code:"04321",
    title:"TMC DRIVER ERROR",
    text:"TMC driver for the Idler motor is not responding. Try resetting the MMU. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_IDLER_DRIVER_ERROR",
  },*/

  E8400: {
    code:"04302",
    title:"TMC DRIVER RESET",
    text:"TMC driver for the Pulley motor was restarted. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_PULLEY_DRIVER_RESET",
  },

  /*E8400: {
    code:"04312",
    title:"TMC DRIVER RESET",
    text:"TMC driver for the Selector motor was restarted. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_SELECTOR_DRIVER_RESET",
  },

  E8400: {
    code:"04322",
    title:"TMC DRIVER RESET",
    text:"TMC driver for the Idler motor was restarted. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_IDLER_DRIVER_RESET",
  },*/

  E8800: {
    code:"04303",
    title:"TMC UNDERVOLTAGE ERR",
    text:"Not enough current for the Pulley TMC driver. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_PULLEY_UNDERVOLTAGE_ERROR",
  },

  /*E8800: {
    code:"04313",
    title:"TMC UNDERVOLTAGE ERR",
    text:"Not enough current for the Selector TMC driver. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_SELECTOR_UNDERVOLTAGE_ERROR",
  },

  E8800: {
    code:"04323",
    title:"TMC UNDERVOLTAGE ERR",
    text:"Not enough current for the Idler TMC driver. There is probably an issue with the electronics. Check the wiring and connectors.",
    text_short:"More details online.",
    id:"TMC_IDLER_UNDERVOLTAGE_ERROR",
  },*/

  E9000: {
    code:"04304",
    title:"TMC DRIVER SHORTED",
    text:"Short circuit on the Pulley TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_PULLEY_DRIVER_SHORTED",
  },

  /*E9000: {
    code:"04314",
    title:"TMC DRIVER SHORTED",
    text:"Short circuit on the Selector TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_SELECTOR_DRIVER_SHORTED",
  },

  E9000: {
    code:"04324",
    title:"TMC DRIVER SHORTED",
    text:"Short circuit on the Idler TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"TMC_IDLER_DRIVER_SHORTED",
  },*/

  EC200: {
    code:"04305",
    title:"MMU SELFTEST FAILED",
    text:"MMU selftest failed on the Pulley TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"MMU_PULLEY_SELFTEST_FAILED",
  },

  /*EC200: {
    code:"04315",
    title:"MMU SELFTEST FAILED",
    text:"MMU selftest failed on the Selector TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"MMU_SELECTOR_SELFTEST_FAILED",
  },

  EC200: {
    code:"04325",
    title:"MMU SELFTEST FAILED",
    text:"MMU selftest failed on the Idler TMC driver. Check the wiring and connectors. If the issue persists contact support.",
    text_short:"More details online.",
    id:"MMU_IDLER_SELFTEST_FAILED",
  },*/

  E800d: {
    code:"04306",
    title:"MMU MCU ERROR",
    text:"MMU detected a power-related issue. Check the wiring and connectors. If the issue persists, contact support.",
    text_short:"More details online.",
    id:"MCU_POWER_ERROR",
  },

  // CONNECTIVITY

  E802e: {
    code:"04401",
    title:"MMU NOT RESPONDING",
    text:"MMU not responding. Check the wiring and connectors.",
    id:"MMU_NOT_RESPONDING",
  },

  E802d: {
    code:"04402",
    title:"COMMUNICATION ERROR",
    text:"MMU not responding correctly. Check the wiring and connectors.",
    id:"COMMUNICATION_ERROR",
  },

  // SYSTEM

  E8005: {
    code:"04501",
    title:"FIL. ALREADY LOADED",
    text:"Cannot perform the action, filament is already loaded. Unload it first.",
    id:"FILAMENT_ALREADY_LOADED",
  },

  E8006: {
    code:"04502",
    title:"INVALID TOOL",
    text:"Requested filament tool is not available on this hardware. Check the G-code for tool index out of range (T0-T4},.",
    id:"INVALID_TOOL",
  },

  E802b: {
    code:"04503",
    title:"QUEUE FULL",
    text:"MMU Firmware internal error, please reset the MMU.",
    id:"QUEUE_FULL",
  },

  E802c: {
    code:"04504",
    title:"MMU FW UPDATE NEEDED",
    text:"The MMU firmware version is incompatible with the printer's FW. Update to compatible version.",
    text_short:"MMU FW version is incompatible with printer FW.Update to version 3.0.0.",
    id:"FW_UPDATE_NEEDED",
  },

  E802f: {
    code:"04505",
    title:"FW RUNTIME ERROR",
    text:"Internal runtime error. Try resetting the MMU or updating the firmware.",
    id:"FW_RUNTIME_ERROR",
  },

  E8008: {
    code:"04506",
    title:"UNLOAD MANUALLY",
    text:"Filament detected unexpectedly. Ensure no filament is loaded. Check the sensors and wiring.",
    id:"UNLOAD_MANUALLY",
  },

  E800c: {
    code:"04507",
    title:"FILAMENT EJECTED",
    text:"Remove the ejected filament from the front of the MMU.",
    id:"FILAMENT_EJECTED",
  },

  // Additional code reported in mmu firmware, but not listed in error-codes.yaml yet. Might need updated if it gets added. Values taken from https://github.com/prusa3d/Prusa-Firmware/blob/MK3/Firmware/mmu2/errors_list.h

  E8029: {
    code:"04508",
    title:"FILAMENT CHANGE",
    text:"M600 Filament Change. Load a new filament or eject the old one.",
    id:"FILAMENT_CHANGE",
  },

  UNKNOWN: {
    code:"04900",
    title:"UNKNOWN ERROR",
    text:"Unexpected error occurred.",
    id:"UNKNOWN_ERROR",
  },
};
