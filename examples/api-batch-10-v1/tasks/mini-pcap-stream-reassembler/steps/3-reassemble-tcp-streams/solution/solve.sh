#!/bin/sh
set -eu
workspace=${TDF_WORKSPACE:-$(pwd)}
mkdir -p "$workspace/environment/codebase/pcap_reassembler"
cp "$(dirname "$0")/files/pcap_reassembler/streams.py" "$workspace/environment/codebase/pcap_reassembler/streams.py"
python3 -m py_compile "$workspace/environment/codebase/pcap_reassembler/streams.py"
