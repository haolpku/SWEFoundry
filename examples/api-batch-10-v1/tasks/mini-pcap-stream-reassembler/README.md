# Classic PCAP TCP Stream Reassembler

`mini-pcap-stream-reassembler` is a five-step, offline Greenfield terminal benchmark candidate in
the `packet capture forensics` domain.

The five cumulative Steps are:

1. `1-parse-classic-pcap-records`
2. `2-decode-ethernet-ipv4-tcp`
3. `3-reassemble-tcp-streams`
4. `4-emit-deterministic-timeout-events`
5. `5-integrated-pcap-audit-recovery`

Primary scoring is strict: only complete behavioral correctness may set
`release_pass` to 1. Auxiliary quality, reasoning and efficiency values cannot
mask a failed behavior check. The verifier fragment declares
41 statically countable checks across the five Steps.

Status: `verifier-audited`. Target-agent rollouts: 0. Difficulty:
`uncalibrated-long-horizon-candidate`.

Source/provenance: concept study of https://github.com/the-tcpdump-group/libpcap (BSD-3-Clause); no upstream
code copied. Distribution remains expert-review-only pending owner approval,
semantic audit, Harbor execution and repeated cross-family calibration.
