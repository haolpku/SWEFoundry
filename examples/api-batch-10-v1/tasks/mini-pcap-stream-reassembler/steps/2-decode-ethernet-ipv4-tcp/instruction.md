Step 2 verification contract: decode Ethernet IPv4 TCP segments while ignoring unsupported frames. Disclosed black-box behavioral gates are ipv4_tcp_segment_public, udp_frame_ignored_public, non_ipv4_ethernet_ignored, ipv4_options_header_length_hidden, tcp_options_data_offset_hidden, fragmented_ipv4_ignored_protocol_validation, packet_index_ordering_hidden, and read_only_state_packets_no_mutation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_02_smoke.py`.
