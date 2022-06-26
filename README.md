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

## Known Bugs

1. In rare events the "waiting for user input" event can come in directly after a tool change is sent resulting in the navbar never updating.nThis will not impact printing but you will see "Awaiting user input" until the next tool change.
1. If the prusa printer prompts the user for a "new version", the select filament modal may not display. You will still be able to select the filament directly on the printer.