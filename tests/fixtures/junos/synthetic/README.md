# Synthetic Junos fixtures

Hand-written `rpc-reply` documents that follow the Junos XML schema as the
collectors expect it. They exercise parsing logic, not real devices.
Addresses, AS numbers, MAC addresses and names are documentation values
(RFC 5737, RFC 3849, RFC 5398, RFC 7042, RFC 2606). Real device captures do
not belong in this repository.

Every directory below `tests/fixtures/junos` is picked up by the structural
tests in `tests/test_exposition.py`. Value assertions only run against this
directory.
