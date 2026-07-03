# Contributing

Thank you for considering contributing!

One of the most valuable ways to help this project is by sharing a small sample of your drone's SRT subtitle file. 
This allows verify compatibility and add support for new SRT formats if possible.

## What to share

A short excerpt is enough—typically 5 subtitle entries**.

The SRT data can come from:

* A standalone `.srt` file stored alongside your video.
* An SRT subtitle track embedded inside an `.mp4` file. The application can extract the embedded SRT for you.

There is **no need to share the entire recording**.

## Privacy

If your SRT contains GPS coordinates or other sensitive information, feel free to **redact or replace them**.

**Please be careful not to break the SRT syntax while editing.** Only replace the values themselves, leaving the overall structure, timestamps, and formatting unchanged.

For example:

```text
GPS(45.123456, 9.654321, 10.4)
```

can become:

```text
GPS(00.000000, 00.000000, 0.0)
```
(Last number is altitude)

can't be : 

```text
GPS(REDACTED, REDACTED, REDACTED)
```

as long as the surrounding syntax remains valid.

## How to submit

You can:

* Open a GitHub Issue and attach the sample.
* Open a Pull Request adding the sample (if appropriate).
* Post the sample in an existing compatibility discussion.

Please mention:

* Drone or camera model
* Firmware version (if known)
* Whether the SRT came from a standalone file or was extracted from the MP4
* Any additional observations that may be useful

Every sample helps make the parser more robust and compatible with more devices. Thank you for contributing!
