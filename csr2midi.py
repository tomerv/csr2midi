import sys
import argparse
from collections import namedtuple
import logging
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo


# Custom logging formatter
class LoggingFormatter:
    def __init__(self):
        pass

    def format(self, record):
        if record.levelno >= logging.WARNING:
            return f"{record.levelname}: {record.msg}"
        else:
            return f"{record.msg}"


def set_logging(verbose=False):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(LoggingFormatter())
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert Casio's digital piano CSR format to MIDI file."
    )
    parser.add_argument("csr_file", type=str, help="CSR file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    return args


# GM is the General Midi standard
Instrument = namedtuple("Instrument", ("name", "gm_equivalent"))


class InstrumentMapping:
    """
    Mapping CSR tone to MIDI instrument ("program")
    """

    # The comments give the names of the General Midi program
    instrument_map = {
        0x0: Instrument("GRAND PIANO VARIATION", 0),  # Acoustic Grand Piano
        0x1: Instrument("GRAND PIANO CLASSIC", 0),  # Acoustic Grand Piano
        0x2: Instrument("GRAND PIANO MODERN", 1),  # Bright Acoustic Piano
        0x400: Instrument("ELEC PIANO", 2),  # Electric Grand Piano
        0x401: Instrument("60'S E. PIANO", 4),  # Electric Piano 1
        0x500: Instrument("FM E. PIANO", 5),  # Electric Piano 2
        0x600: Instrument("HARPSICHORD", 6),  # Harpsichord
        0xB00: Instrument("VIBRAPHONE", 11),  # Vibraphone
        0x1000: Instrument("ELEC ORGAN 1", 20),  # Reed Organ
        0x1001: Instrument("ELEC ORGAN 2", 17),  # Percussive Organ
        0x1100: Instrument("JAZZ ORGAN", 16),  # Drawbar Organ
        0x1300: Instrument("PIPE ORGAN", 19),  # Drawbar Organ
        0x3000: Instrument("STRINGS 2", 51),  # Synth Strings 2
        0x3100: Instrument("STRINGS 1", 50),  # Synth Strings 1
    }

    @classmethod
    def to_midi(cls, csr_tone: int):
        return cls.instrument_map[csr_tone]


def convert(data) -> MidiFile:

    signature = data[:4]
    if not signature == b"SP5F":
        logging.warning(f"Invalid signature: {signature}")

    model = data[4:12]
    logging.info(f"Model: {model.decode('utf-8')}")
    if model != b"PX-130  ":
        logging.warning(f"Unsupported model: {model}")

    if not data[0x0C:0x10] == data[0x118:0x11C]:
        logging.warning(f"Inconsistent file size (1)")
    file_size = int.from_bytes(data[0x0C:0x10], byteorder="little")
    logging.info(f"Original file size: {file_size} bytes")
    file_size += 0x114
    if len(data) != file_size:
        logging.warning(f"Inconsistent file size (2): {len(data):#x}, {file_size:#x}")

    if not data[0x16F] == data[0x198]:
        logging.warning(f"Inconsistent BPM")
    bpm = data[0x16F]
    logging.info(f"BPM: {bpm}")

    tone = int.from_bytes(data[0x164:0x166], byteorder="big")
    instrument = InstrumentMapping.to_midi(tone)
    logging.info(f"Tone: {instrument.name}")

    marker = b"\xf1\x80\x00" * 12
    pos = data.find(marker)
    assert pos > 0, "Could not find marker"
    tracks_data = data[pos + len(marker) :]

    logging.info("")

    midi_output = MidiOutput(bpm, instrument.gm_equivalent)

    # tempo converter
    def csr_ticks_to_midi_ticks(n: int) -> int:
        """Time conversion"""
        beats = n / 0x60
        ticks = int(beats * midi_output.midi_file.ticks_per_beat)
        return ticks

    # tracks
    convert_track_data(tracks_data, midi_output, csr_ticks_to_midi_ticks)

    return midi_output.midi_file


class MidiOutput:
    """
    Simple wrapper for outputing MIDI file.
    Provides the functionality needed for CSR files, and hides the rest.
    """

    def __init__(self, bpm, program):
        self.midi_file = MidiFile()
        self.bpm = bpm
        self.program = program
        self.midi_track = None

        # start first track
        first_track = MidiTrack()
        self.midi_file.tracks.append(first_track)
        self._init_first_track(first_track)
        self.midi_track = first_track

    def damper_pedal(self, value, time_delta):
        message = Message(
            "control_change",
            control=0x40,
            value=value,
            time=time_delta,
        )
        self.midi_track.append(message)

    def note(self, note, velocity, time_delta):
        message = Message(
            "note_on",
            note=note,
            velocity=velocity,
            time=time_delta,
        )
        self.midi_track.append(message)

    def next_track(self, time_delta):
        if time_delta > 0 and len(self.midi_file.tracks) == 1:
            # track 0 is the "main" track
            # reset all controllers
            message = Message("control_change", control=0x79, value=0, time=time_delta)
            self.midi_track.append(message)
        # new track
        midi_track = MidiTrack()
        self.midi_file.tracks.append(midi_track)
        message = Message("program_change", program=self.program, time=0)
        midi_track.append(message)
        self.midi_track = midi_track

    def _init_first_track(self, track):
        """First MIDI track has all the meta messages."""

        # time signature
        # CSR does not contain the time signature for the metronome, and it is always reset to 4/4
        track.append(
            MetaMessage(
                "time_signature",
                numerator=4,
                denominator=4,
                clocks_per_click=24,
                notated_32nd_notes_per_beat=8,
            )
        )

        # tempo
        tempo = bpm2tempo(self.bpm)
        track.append(MetaMessage("set_tempo", tempo=tempo))
        ticks_per_beat = self.midi_file.ticks_per_beat
        logging.debug(f"MIDI tempo={tempo}, ticks_per_beat={ticks_per_beat}")

        # reset all controllers
        # control 0x79 == all controllers
        track.append(Message("control_change", control=0x79, value=0, time=0))

        # instrument
        message = Message("program_change", program=self.program, time=0)
        track.append(message)


def convert_track_data(tracks_data, midi_output, time_converter):
    # State machine with 2 alternating states:
    # 1. time delta
    # 2. command
    expecting_time_delta = False
    pos = 0
    time_delta = 0
    while pos < len(tracks_data):
        if expecting_time_delta:
            delta = tracks_data[pos]
            logging.debug(f"Got time delta {delta}")
            time_delta += delta
            pos += 1
            expecting_time_delta = False
            continue
        command = tracks_data[pos]
        value = tracks_data[pos + 1]
        pos += 2
        expecting_time_delta = True
        if command == 0xF2:  # unknown command...
            logging.debug(f"Got command {command:#x} with value {value}")
            if not (value == 66) and not (value == 82):
                logging.warning(f"Unexpected command {command:#x} with value {value}")
        elif command == 0xFC:  # next track
            logging.debug(f"Got next-track command with value {value}")
            if value != 0:
                logging.warning(f"Unexpected value {value}")
            midi_output.next_track(time_converter(time_delta))
            time_delta = 0
        elif command == 0xFF:  # delay
            logging.debug(f"Got delay command with value {value}")
            time_delta += 256 * value
        elif command == 0xB1:  # damper pedal
            logging.debug(f"Got damper pedal with value {value}")
            midi_output.damper_pedal(value, time_converter(time_delta))
            time_delta = 0
        elif command < 0x80:  # note
            logging.debug(f"Got note {command:#x} with value {value}")
            if (command < 0x15) or (command > 0x6C):
                logging.warning(f"Note {command:#x} is outside of valid piano range")
            # velocity is already in the correct range
            midi_output.note(command, value, time_converter(time_delta))
            time_delta = 0
        else:
            logging.warning(f"Got unknown command {command:#x} with value {value}")


if __name__ == "__main__":
    set_logging()
    args = parse_args()
    if args.verbose:
        logging.root.setLevel(logging.DEBUG)
    filename = args.csr_file
    with open(filename, "rb") as f:
        data = f.read()
    midi_file = convert(data)
    midi_filename = filename[:-4] + ".mid"
    midi_file.save(midi_filename)
    logging.info(f"Saved to {midi_filename}")
