# Octoprint-PrusaMMU

**Description:** This plugin adds Prusa MMU2 support to OctoPrint. The active filament will be
displayed in the navbar and you will be prompted to select which filament to use when slicing in
"MMU2S Single" mode. Other settings are available to name each tool and set defaults. This plugin
only works for a Prusa printer with an MMU2.

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually by selecting the latest zip:

    https://github.com/jukebox42/Octoprint-PrusaMMU/releases/latest/download/Octoprint-PrusaMmu.zip

## Note

This plugin does some minimal gcode manipulation. This is how it detects tool events.

The command interactions are as follows:
- Before sent: (gcode_queuing_hook)
  - `Tx`: When the GCODE would send a `Tx` (tool change) it first triggers the modal and then does
    not send the Tx command. Instead it sends a pause event to the printer. This results in Prusa
    not prompting for a tool change. If the timeout time is reached (`_timeout_prompt`) then the
    plugin resends the `Tx` command to allow Prusa to prompt the user.
  - `M109`: When the GCODE would send an `M109` (Wait for Hotend Temperature) and the user
    has selected a filament we send both the `M109` and `T#` (like `T2`), otherwise we just send the
    `M109`.
- After sent: (gcode_sent_hook)
  - When the plugin notices a `T#` command we set the tool internally so it can be used to
    display. This is to support multi-color printing. This trigger is also used to show unloading.

We listen to printer responses and do some substring matching. This is done to identify filament
events and printer notifications so we can update the navbar: (gcode_received_hook)
  - `paused for user` - Used to show that the printer needs attention (eithe error or waiting for
    tool selection at printer).
  - `MMU not responding` -  Used to show that the printer needs attention because of an MMU failure.
  - `MMU - ENABLED` / `MMU starts responding` - Used to show printer is "OK".
  - `MMU can_load` - Used to show the filament loading message.
  - `OO succeeded` - Used to show what filament is loaded.

For all instances of where command manipulation happens see `__init__.py` for `Gcode Hooks`. Also
look at function `_timeout_prompt` where we handle unpausing the printer after the timer and either
sending a `Tx` or `T#` if `useDefaultFilament` and `defaultFilament` settings are set.

## Configuration

- Set a timeout to auto-select an extruder
- Enable/disable extruders, name them and give them a color
- Show/hide navbar item (and simplify the display)

## Screenshots

![Modal](/screenshots/modal.png)

![Navbar](/screenshots/nav.png)

![Settings](/screenshots/settings.png)

## Building

You can manually build this project into a zip by running:
```
$ bash build.sh [VERSION DEBUG]

# ex:
$ bash build.sh 2022.7.4 n
=== Building PrusaMMU ===

Settings:
- Version: 2022.7.4
- Debug n

Writing plugin version... done
Disabling debug... done
Zipping... done
Done.
```

- Version expects a string (optional, defaults to YYYY.M.Dalpha)
- Debug turns on and off debug logs in the plugin, expects a y/n (optional, defaults to y)

### Versioning

Versioning is done by date so it's clear when the build was installed and made available. Year is
four characters long. Month is one or two characters long depending and does not have a leading zero
for sub ten. Day follows the same rules as month. Beta versions are denoted by a "b" directly
following the day and then a number describing what beta version it is. Sequentially `2022.1.1b1`
comes before `2022.1.1`.

Format:
```
YYYY.M.D
YYYY.M.Db#
```

Examples:
```
2022.10.4
2022.1.20
2022.1.20b2
```

Note: Beta versions will have debug enabled. When debug is on the plugin will be noisier. It will
console.log a lot of interactions and the nav bar item will link to the plugin manifest instead of
the plugin settings.

## Known Bugs

1. In rare instances, the "waiting for user input" event can come in directly after a tool change is
   sent, resulting in the navbar never updating. This will not impact printing but you will see
   "Awaiting user input" until the next tool change.
1. If the Prusa printer prompts the user for a "new version", the select filament modal may not
   display. You will still be able to select the filament directly on the printer.
1. If settings are saved mid-print the navbar will forget the state of the MMU. This does not impact
   printing but is rather annoying. It'll remember the next time the tool changes.

## Contribution

I built this plugin for fun, and because I wanted better MMU support. If you catch a bug or think it
needs some work feel free to open a PR and I'll do my best to review it.

If you can figure out how to get the MMU state data (when it's errored) please let me know and I'll
add it. I tried to find it but was unsuccessful.

## Useful Link
- [MMU2 Commands](https://cfl.prusa3d.com/display/PI3M3/MMU2+commands)
- [Debugging MMU2](https://revilor.github.io/MMU2-Marlin/debugging.html)
- [MMU2 LEDs Meaning](https://help.prusa3d.com/article/mmu2s-leds-meaning_2187#red-light)
- [Octoprint Plugin Docs](https://docs.octoprint.org/en/master/plugins/mixins.html)