# Octoprint-PrusaMMU

**Description:** This plugin only works with a Prusa printer paired with an MMU2S. This plugin prompts you to select the filament when starting a print that was sliced with "MMU2S Single" instead of forcing you to be at your printer. It additionally lets you name and color the filament in each extruder. The active filament will be displayed in the navbar.

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually by selecting the latest zip:

    https://github.com/jukebox42/Octoprint-PrusaMMU/releases/

## Configuration

- Set a timeout to auto-select an extruder
- Enable/disable extruders, name them and give them a color
- Show/hide navbar item

## Screenshots

![Modal](/screenshots/modal.png)

![Navbar](/screenshots/nav.png)

![Settings](/screenshots/settings.png)

## Building

You can manually build this project into a zip by running:
```
$ bash build.sh [VERSION DEBUG]

# ex:
$ bash build 2022.7.4 n
=== Building PrusaMMU ===

Settings:
- Version: 2022.7.4
- Debug n

Writing plugin version... done
Disabling debug... done
Zipping... done
Done.
```

- Version expects a string (optional, defaults to BETA)
- Debug turns on and off debug logs in the plugin expects a y/n (optional, defaults to y)

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
````
2022.10.4
2022.1.20
2022.1.20b2
```

Note: Beta versions will have debug enabled. When debug is on the plugin will be noisier. It will
console.log a lot of interactions and the nav bar item will link to the plugin manifest instead of
the plugin settings.

## Known Bugs

1. In rare events the "waiting for user input" event can come in directly after a tool change is sent resulting in the navbar never updating.nThis will not impact printing but you will see "Awaiting user input" until the next tool change.
1. If the prusa printer prompts the user for a "new version", the select filament modal may not display. You will still be able to select the filament directly on the printer.