Step 3 verification contract: reassemble deterministic TCP streams by canonical five-tuple flow key. Disclosed black-box behavioral gates are out_of_order_reassembled_public_sequence_order, retransmission_deduplicated_public, overlap_resolution_first_byte_wins_hidden, syn_sequence_base_normalization_hidden, canonical_flow_key_sorting_hidden, fin_sets_closed_state_hidden, gap_summary_hidden_overlap_resolution, and read_only_state_segments_no_mutation.

## Public contract self-check

Read `/app/knowledge/public_api.md` before implementation. From `/app/workspace`, run `python public_contract_tests/step_03_smoke.py`.
