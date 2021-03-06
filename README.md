# About

csr2midi is a tool to convert the proprietary Casio CSR file format to MIDI file.

It currently supports files copied from the PX-130 and PX-160 models.
If you're interested in support for more models, please open an issue.


# Recorded data

According to the PX-130 User's Guide, the following data is recorded.
Support in csr2midi is marked with `[x]` or `[ ]`.

* [x] Keyboard play
* [x] Tone used
  * csr2midi only supports tone setting for the left channdel
* [x] Pedal operations
  * csr2midi only supports damper (sustain) pedal
* [ ] Reverb and chorus settings (Track 1 only)
* [x] Tempo setting (Track 1 only)
* [ ] Layer setting (Track 1 only)
* [ ] Split setting (Track 1 only)
* [ ] Temperament and base note setting (Track 1 only)
* [ ] Octave shift setting (Track 1 only)


# Requirements

## Windows (64-bit)

You can download and run the packaged release, see [Releases page](https://github.com/tomerv/csr2midi/releases).

## Running from source code

You will need:

* [Python 3.7](https://www.python.org/downloads/) or newer
* [mido](https://pypi.org/project/mido/)


# Tests

All tests are from PX-130 except where noted otherwise.

1. Chromatic scale over all the keyboard
2. Single note for 20 seconds
3. Two channels in sync
4. Simple cadence
5. Short segment from Chopin's Nocturne
6. Example from PX-160
