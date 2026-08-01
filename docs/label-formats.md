# Track Label Formats

Track labels are edited in-app under **Windows -> Track Labels**. Each object type
(fixed wing, rotary wing, missile, ground, sea) has its own set of labels, and each label
is placed at one of nine positions around the track icon.

A label is a template string. Anything in `{curly braces}` is replaced with a value from
the track; everything else is printed literally.

    {display_name}                    ->  Viper11
    {altitude_ft_floor100:.0f}ft      ->  24600ft
    ANGELS {altitude_1000ft:.0f}      ->  ANGELS 25

All examples below use the same track: callsign `Viper11` at 24,606 ft, Mach 0.85,
389 kt, bullseye 059/31.

## Formatting numbers

Values support Python format specs after a colon. The common one is `:.Nf`, which sets
the number of decimal places:

| Template | Result |
|---|---|
| `{Mach}` | `0.8532000184059143` |
| `{Mach:.2f}` | `0.85` |
| `{altitude_ft:.0f}` | `24606` |

Without a format spec, raw floating point values are long and noisy - `:.0f` or `:.2f` is
almost always what you want.

## Show on hover

Each label has a **show on hover** toggle. Labels with it enabled are only drawn when the
cursor is over that track. This keeps the display readable, and it is also much cheaper -
hover labels are skipped entirely until you hover, so they cost effectively nothing.

The shipped defaults use always-on labels for aircraft and hover-only labels for ground,
sea and missiles.

## Available variables

### Convenience values

These are computed for you and are usually what you want:

| Variable | Meaning |
|---|---|
| `display_name` | Best available name: callsign, pilot, name, or type |
| `altitude_ft` | Altitude in feet |
| `altitude_100ft` | Altitude in hundreds of feet (flight-level style) |
| `altitude_1000ft` | Altitude in thousands of feet (angels) |
| `altitude_ft_floor100` | Altitude in feet, rounded down to the nearest 100 |
| `speed_kt` | Calibrated airspeed in knots |
| `magnetic_heading` | Heading in degrees, magnetic if enabled in settings |
| `bullseye` | Bearing and range from bullseye - see below |

### Aliases

| Alias | Equivalent to |
|---|---|
| `id` | The object's ID |
| `name` | Same as `display_name` |
| `type` | Object type, e.g. `FIXEDWING` |

### Bullseye

`bullseye` is a pair of values, so index it to pick one:

`bullseye[0]` is the bearing in degrees, `bullseye[1]` is the range in nautical miles.

Bearings are conventionally written as three digits, with leading zeros. Use `:03.0f` for
that - `03` means "pad to at least 3 characters with zeros" and `.0f` means "no decimal
places":

    {bullseye[0]:03.0f}                   ->  059
    {bullseye[0]:03.0f}/{bullseye[1]:.0f} ->  059/31

Without the padding you get bare numbers, which read poorly for low bearings:

| Template | Bearing 3 | Bearing 59 | Bearing 297 |
|---|---|---|---|
| `{bullseye[0]:.0f}` | `3` | `59` | `297` |
| `{bullseye[0]:03.0f}` | `003` | `059` | `297` |

The same trick works for any bearing-like value, for example
`{magnetic_heading:03.0f}`.

### Raw telemetry fields

Any field BMS sends is available under its raw name. These are unconverted - `Altitude`
is in metres, `CAS` and `IAS` are in metres per second:

`AOA`, `AOS`, `Altitude`, `CAS`, `CallSign`, `Coalition`, `Color`, `FuelWeight`, `Group`,
`Heading`, `Health`, `IAS`, `LateralGForce`, `Latitude`, `Longitude`,
`LongitudinalGForce`, `Mach`, `Name`, `Pilot`, `Pitch`, `Roll`, `Type`, `U`, `V`,
`VerticalGForce`, `Yaw`, `LockedTarget` (and `LockedTarget1` through `LockedTarget9`)

Note that not every field is populated for every object - what BMS reports depends on the
object type and on what the Tacview Real-Time Telemetry protocol exposes.

## When something is wrong

If a label references a name that does not exist, the label renders an error message in
place of the value rather than crashing. Check the spelling against the tables above -
names are case sensitive, so `{mach}` will not work but `{Mach}` will.

## Examples

    {display_name}
    Viper11

    {altitude_ft_floor100:.0f}ft M{Mach:.2f}
    24600ft M0.85

    {bullseye[0]:03.0f}/{bullseye[1]:.0f}
    059/31

    {display_name} | {altitude_1000ft:.0f}k | {speed_kt:.0f}kt
    Viper11 | 25k | 389kt
