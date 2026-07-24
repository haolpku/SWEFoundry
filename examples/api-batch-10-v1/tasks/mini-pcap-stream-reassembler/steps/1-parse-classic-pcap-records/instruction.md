Step 1 verification contract: parse classic PCAP records from bytes. Disclosed black-box behavioral gates are little_endian_single_packet_public, big_endian_declared_magic_hidden_endianness_decoding, truncated_record_header_raises_valueerror_public, captured_length_exceeds_snaplen_hidden_bounds, captured_length_exceeds_original_hidden_bounds, timestamp_microseconds_range_hidden_data_field, record_ordering_indices_hidden_record_ordering, and read_only_state_repeated_parse_no_mutation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_01_smoke.py`.
