# File Structure

    --- HEADER ---

    @ 0x0
      14 bytes
      file signature
      "SP5FPX-130  "

    @ 0xc
      2 bytes, little endian
      file size
      appear again @ 0x118
      need to add 0x114 to get the total file size
      0x114 is the size of the header block

    @ 0x10
      260 bytes
      all 0's

    --- END OF HEADER ---

    --- START "CMLF" BLOCK ---

    @ 0x114
      4 bytes
      "CMLF"

    @ 0x118
      2 bytes, little endian
      size of CMLF block
      need to add 0x114 to get the total file size
      0x114 is the offset of the start of the CMLF block

    @ 0x11c
      4 bytes
      "0001"

    @ 0x120
      46 bytes
      ???

    @ 0x14e
      2 bytes, little endian
      remaining bytes until EOF (starting from 0x14e)

    @ 0x150
      20 bytes
      ???
      
    @ 0x164
      2 bytes, BIG ENDIAN
      base tone (instrument)
      0x0 - variation grand piano
      0x1 - classic grand piano
      0x2 - modern grand piano (default for PX-130)
      0x400 - elec piano
      ...

    @ 0x166
      2 bytes, BIG ENDIAN
      layered tone (instrument)

    @ 0x168
      2 bytes
      something with tone layering...
      0x1000 = regular layering?
      0x2000 = bass layering???

    @ 0x169
      5 bytes
      ???

    @ 0x16e
      1 byte
      something with tone layering...

    @ 0x16f
      1 byte
      metronome bpm
      appears again @ 0x198

    @ 0x170
      40 bytes
      ???

    @ 0x198
      1 byte
      metronome bpm (see @ 0x16f)

    @ 0x199
      87 bytes
      ???

    @ 0x1f0
      128 bytes
      ???
      it's like each "row" is an addition equation...

    @ 0x270
      8 bytes
      ???

    @ 0x278
      24 bytes
      start marker
      b"\xf1\x80\x00" * 12

    @ 0x29c
      variable length (3k-1 bytes for k commands)
      recording section

    --- START "CMLF" BLOCK ---

    --- EOF ---


# Recording section

The recording section of the CSR file is a series of

    <command + value> (2 bytes)
    <delay> (1 bytes)
    <command + value> (2 bytes)
    <delay> (1 bytes)
    .
    .
    .
    <command + value> (2 bytes)

The total size is 3k-1 bytes for k commands.

## Delay

The delay is given "ticks", where each tick is 1/96 of a beat.
For example, a delay of 1/4 beat will be 24 ticks, or 0x18.
The delay is 1 byte, so the maximum delay between commands is 0xff ticks, or 255/96 of a beat.
The 0xff command is used to add more dealy.

## Commands

The known commands are:

0x15-0x6c = press or release key
  The command is the key to press or release, where 0x3c is middle C.
  The value following is the velocity with which the key was pressed, or 0 if the key was released.

0xb1 = press or release damper pedal
  value = 0x7f for pressing
  value = 0x0 for releasing

0xf1 = ???
  This appears 12 times in a row at the start of the first track, with value 128.
  It's used by csr2midi as the marker for the start of the recording area.

0xf2 = ???
  This appears twice at the start of the first track (after 0xf1), with value 66 and then with value 82.

0xfc = next track
  The first CSR file starts on the first track (track 0), and each 0xfc command moves to the next track.
  The value is always 0x0.
  There is no "previous track" command.
  The PX-130 has 2 recording tracks, L and R. In the CSR file they are track 0 and track 15.
  This means that for PX-130 there will be 15 "next track" commands in a row.

0xff = delay
  Used to extend the delay until the next command.
  The number of ticks to delay is the value times 0x100.
  For example, if the value is 2 then need to add a delay of 0x200 = 512 ticks.

Other commands are not known.
