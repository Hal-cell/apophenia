"""Audio capture + feature extraction.

The `source` module defines the `AudioSource` Protocol; `mock`, `file`, and
`device` provide three interchangeable implementations. Downstream code
never imports an implementation directly — it works with whatever
`source.parse_source_arg(cli_arg)` returns.
"""
