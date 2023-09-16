# Octoprint-PrusaMMU

**Description:** This plugin adds Prusa MMU2 support to OctoPrint. The active filament will be
displayed in the navbar and you will be prompted to select which filament to use when slicing in
"MMU2S Single" mode. Other settings are available to name each tool and set defaults. This plugin
only works for a Prusa printer with an MMU2. Supports MMU firmware `1.X.X` and `3.X.X`.

This plugin was inspired by the [MMU2filamentselect](https://plugins.octoprint.org/plugins/mmu2filamentselect/)
plugin. I wanted to try and take it a step further.

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually by selecting the latest zip:

    https://github.com/jukebox42/Octoprint-PrusaMMU/releases/latest/download/Octoprint-PrusaMmu.zip

## Configuration

- Set a timeout to auto-select an extruder
- Enable/disable extruders, name them, and give them a color
- Show/hide navbar item (and simplify the display)
- Supports retrieving filament data from [Spool Manager](https://plugins.octoprint.org/plugins/SpoolManager/)
  and [Filament Manager](https://plugins.octoprint.org/plugins/filamentmanager/) if installed.

## Screenshots

![Modal](/screenshots/modal.png)

![Navbar](/screenshots/nav.png)

![Settings](/screenshots/settings.png)

## GCode Interactions

This plugin does some minimal gcode manipulation. This is how it detects tool events and pause the
print to provide the dialog.

The command interactions are as follows:
- Before sent: (gcode_queuing_hook)
  - `Tx`: When the GCODE would send a `Tx` (tool change) it first triggers the modal and then does
    not send the Tx command. Instead, it sends a pause event to the printer. This results in Prusa
    not prompting for a tool change. If the timeout time is reached (`_timeout_prompt`) then the
    plugin resends the `Tx` command to allow Prusa to prompt the user.
  - `M109`: When the GCODE would send an `M109` (Wait for Hotend Temperature) and the user
    has selected a filament we send both the `M109` and `T#` (like `T2`), otherwise we just send the
    `M109`.
- After sent: (gcode_sent_hook)
  - When the plugin notices a `T#` command we set the tool internally, so it can be used to
    display. This is to support multicolor printing. This trigger is also used to show unloading.

We listen to printer responses and do some substring matching. This is done to identify filament
events and printer notifications, so we can update the navbar: (gcode_received_hook)
  - `paused for user` - Used to show that the printer needs attention (either error or waiting for
    tool selection at printer).
  - `MMU not responding` -  Used to show that the printer needs attention because of an MMU failure.
  - `MMU - ENABLED` / `MMU starts responding` - Used to show printer is "OK".
  - `MMU can_load` / `Unloading finished` - Used to show the filament loading message.
  - `OO succeeded` - Used to show what filament is loaded.

MMU2/3 3.X.X:

The MMU 3.x.x firmware communicates continuously with the printer. The printer sends the MMU
Requests, and the MMU sends back Responses. The MMU's Responses start with the Request Letter and
Data, so we just listen for the Responses.

MMU 3.x.x responses come in this format:  
`MMU2:<(Request Letter)(Request Data) (Response Letter)(Response Data)`
  - `(Request Letter)` - A single letter code that represents a request sent from the printer to the MMU.
    - We only listen for `T` - Tool, `L` - Load, `U` - Unload, `X` - Reset, `K` - Cut, and `E` - Eject.
  - `(Request Data)` - Hexidecimal data that follows the Request Letter.
    - It's usually `0`, unless the request involves filament, in which case it is the filament number `[0-4]`.
  - `(Response Letter)` - A single letter code that represents a response from the MMU.
    - Possible responses are `P` - Processing, `E` - Error, `F` - Finished, `A` - Accepted,
      `R` - Rejected, and `B` - Button.
  - `(Response Data)` - Hexidecimal data that follows the Response Letter.
    - The amount of data varies depending on the Request Letter and Response Letter.
    - We only use Response Data to decode `P` - Progress messages, and `E` - Error messages

Several Regex strings are used to parse the MMU 3.x.x responses:
  - `MMU2:<[TLUXKE]` - Generic Regex used to catch the responses with the Request Letters that are important.
  - `MMU2:<([TLUXKE])(.*) ([PEFARB])(.*)\*` - Used to split the command into the four groups described above.

Additionally, we also listen for these other lines:
  - `MMU2:Saving and parking` - Used to detect when the printer is waiting for user input after the
    MMU fails at auto-retrying after an Error.
  - `MMU2:Heater cooldown pending` - The same as above. Might be unecessary, but I included both
    just in case.
  - `LCD status changed` - If the printer is paused, this tells us that the pause is probably over.

For all instances of where command manipulation happens see `__init__.py` for `Gcode Hooks`. Also
look at function `_timeout_prompt` where we handle unpausing the printer after the timer and either
sending a `Tx` or `T#` if `useDefaultFilament` and `defaultFilament` settings are set.

## Known Bugs

1. In rare instances, the "waiting for user input" event can come in directly after a tool change is
   sent, resulting in the navbar never updating. This will not impact printing, but you will see
   "Awaiting user input" until the next tool change.
1. If the Prusa printer prompts the user for a "new version", the select filament modal may not
   display. You will still be able to select the filament directly on the printer.

## Developer Zone

### States

Here is a list of states used internally. These will be the `state` value in events.

- `NOT_FOUND` - MMU not found, this is an initial state before a printer connects.
- `STARTING` - When a printer with an MMU is connected it goes through a startup. This is triggered
  first followed by `OK` when it replies it's enabled.
- `OK` - Triggered when a print job finishes (or cancels) and when the mmu reports healthy on
  printer connect.
- `LOADED` - Filament (tool) is loaded.
- `UNLOADING` - Filament (tool) is unloading.
- `LOADING` - Filament (tool) is loading OR unloading has concluded.
- `PAUSED_USER` - Printer is awaiting user input OR filament dialog is present.
- `ATTENTION` - Printer needs user attention, could be MMU error or printer prompt (like new
  software version available).
- `LOADING_MMU` - MMU is preloading filiment to the MMU (not to nozzle)
- `CUTTING` - MMU is cutting the filament
- `EJECTING` - MMU is ejecting the filament

### Errors

New when using MMU 3.0.0!

When the MMU throws an error you'll see a command come across like `MMU2:<X0 E800d`. The `E`
Response Letter represents there being an Error and the `800d` is the hex Response Data of the error.

We map those hex codes in `static/mmuErrors.js` to get the details about the errors. Mapping was
done by hand (i'll automate it eventually). To get the url of the error you just need to append the
`code` value from the `MMU2MmuErrorStrings` map to `https://prusa.io/` like `https://prusa.io/04306`.

### Events

A number of events are fired you can listen to.

#### `plugin_prusammu_mmu_changed`

MMU data changed; Either state, tool, previous tool, response, or response data was updated.

Payload:
```javascript
{
  state: string
  tool: int
  previousTool: int
  response: string
  responseData: string
}
```

#### `plugin_prusammu_mmu_change`

MMU data _may_ change. This is fired by a number of things internal to the plugin, what's important
is that this does not indicate a change happened, just that one _may_ happen. It's strongly
recommended to listen on `plugin_prusammu_mmu_changed` instead unless you need to react before a
change occurs. The plugin internally dedupes these events by comparing the new with the old and only
triggering when there's a change. 

Payload:
```javascript
{
  state: string
  tool: int
  previousTool: int
  response: string
  responseData: string
}
```

#### `plugin_prusammu_show_prompt`

The plugin heard a `Tx` and needs to prompt the user to pick the filament. 

Payload: `None`

#### `plugin_prusammu_refresh_nav`

Used to force the UI to refresh it's MMU data (like on page refresh).

Payload: `None`

### Exposed Javascript Functions

A small set of javascript functions are available to interact with. Look at the `getFilamentList()`
function for how you can interact with them.

#### `getFilamentList()`

Returns the filament array. This will contain all the filament data based on the source selected.
This is what's used to get the data for the prompt as well as navbar item. The resultset may include
1-5 entries based on what's specified by the source.

Returns:
```javascript
[
  {id: 1, index: 0, name: "", type: "", color: "", enabled: true},
  {id: 2, index: 1, name: "", type: "", color: "", enabled: true},
  {id: 3, index: 2, name: "", type: "", color: "", enabled: true},
  {id: 4, index: 3, name: "", type: "", color: "", enabled: true},
  {id: 5, index: 4, name: "", type: "", color: "", enabled: true},
]
```

Filament object properties:
- `id` - The ID of the filament (the index +1, so it's readable and because I wanted to make it hard
  on myself)
- `index` - The real index of the filament (tool) as the printer would see it.
- `name` - The name the user gave the filament.
- `type` - The type of filament (i.e. PLA/PETG). This is blank unless the source is filamentManager
  or spoolManager.
- `color` - The color of the filament.
- `enabled` Whether the filament is enabled in prusammu (when using prusammu as the source).

#### `processMmuProgress(responseData)`

Given the progress code it returns a string containing the progress message.

If the value of `responseData` is one of [`P`, `E`, `F`, `A`, `R`] than you can pass `responseData`
to get more details about the progress like `"Unloading to FINDA"`.

Returns: `string`

#### `processMmuError(responseData)`

Given the error code it generates an error object with more information.

If the value of `response` is `E` (Error) you can send this function `responseData` to get the
error details.

Returns:
```javascript
{
  code: "04401",
  title: "MMU NOT RESPONDING",
  text: "MMU not responding. Check the wiring and connectors.",
  url: `https://prusa.io/802e`,
}
```

Object properties:
- `code` - The error code.
- `title` - The name of the error.
- `text` - The description of the error.
- `url` - The Prusa short url of the error. These are formatted like: `https://prusa.io/{code}`.

## Working on the PrusaMMU plugin

### Adding a Filament Source

If you too would like to add your filament/spool manager as a valid source for this plugin you need
to update the following areas:

- `__init__.py`
    - Update `on_after_startup()` to detect your plugin.
- `templates/prusammu_settings.jinja2`
    - Add a link to your plugin in the helptext of `Filament Label Source`.
    - Add an `alert` box identifying how filament is set in your plugin.
- `static/prusammu.js`
    - Set your plugin as a dependency AND optional for `PrusaMMU2ViewModel` (bottom of file) 
    - Add your plugin in the `self.filamentSources` object.
    - Update the `getFilamentList()` function to call your filament/spool function. This will require
    your plugin to expose a javascript function the returns a list of filament and what tool they
    represent.

### Debugging

Enable debug logs via the settings menu, ensure logging is set to the debug level for prusammu.
Note: This may slow down printing.

Octoprint exposes the viewmodel via:
```javascript
> OctoPrint.coreui.viewmodels.prusaMMU2ViewModel
```

### Building

You can manually build this project into a zip by running:
```
$ bash build.sh [VERSION]

# ex:
$ bash build.sh 2022.7.4
=== Building PrusaMMU ===

Settings:
- Version: 2022.7.4

Writing plugin version... done
Disabling debug... done
Zipping... done
Done.
```

- Version expects a string (optional, defaults to YYYY.M.Dalpha)
- Debug turns on and off debug logs in the plugin, expects a y/n (optional, defaults to y)

### Versioning

Versioning is done by date, so it's clear when the build was installed and made available. Year is
four characters long. Month is one or two characters long and does not have a leading zero
for sub ten. Day follows the same rules as month. Beta versions are denoted by a "b" directly
following the day and then a number describing what beta version it is. Sequentially `2022.1.1a0`
comes before `2022.1.1`.

Format:
```
YYYY.M.D
YYYY.M.Da#
```

Examples:
```
2022.10.4
2022.1.20
2022.1.20a0
```

### Contribution

I built this plugin for fun, and because I wanted better MMU support. If you catch a bug or think it
needs some work feel free to open a PR or cut an issue, and I'll do my best to review it.

If you can figure out how to get the MMU state data (when it's errored) please let me know, and I'll
add it. I tried to find it but was unsuccessful.

Special thanks to:
- [@skellied](https://github.com/skellied) for help with the initial release of MMU 3.0.0 support.
- [@Kevman323](https://github.com/Kevman323) for a significant revamp of the MMU 3.0.0 code,
  cleaning up error codes, and bringing in more data to the nav.

## Useful Link
- [MMU2 Commands](https://cfl.prusa3d.com/display/PI3M3/MMU2+commands)
- [Debugging MMU2](https://revilor.github.io/MMU2-Marlin/debugging.html)
- [MMU2 LEDs Meaning](https://help.prusa3d.com/article/mmu2s-leds-meaning_2187#red-light)
- [Octoprint Plugin Docs](https://docs.octoprint.org/en/master/plugins/mixins.html)
