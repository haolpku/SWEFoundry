# Sandbox model

Yes, these tasks require a sandbox. An agent is explicitly asked to inspect and modify code and may execute arbitrary commands while doing so. Treat both candidate task content and agent output as untrusted.

## Trial sandbox

- Create one ephemeral container or microVM per rollout; never reuse a writable layer between agents.
- Run without privilege, host PID/network namespaces, host credentials, or the Docker/gongfeng control socket.
- Drop Linux capabilities, apply seccomp/AppArmor, set PID/CPU/memory/storage/time limits, and disable outbound network unless a task has a reviewed network requirement.
- Mount only public workspace/evidence during the agent phase. Do not place solution, verifier, rollout labels, or other instances in the image.
- Export only allowlisted artifacts and Harbor traces. Reject symlinks, devices, sockets, and paths escaping the artifact root.

## Scoring isolation

Harbor uploads `tests/**` only for verification. These tasks set `environment_mode = "separate"`, so scoring runs in a fresh verifier environment built from the final `/app/workspace` artifact and a separate tests bundle. The agent image contains neither solution nor verifier files.

The managed three-host pool rejects Harbor's nftables sidecar under user namespaces. `harbor_ext.static_no_network` is a constrained compatibility backend for these single-container tasks: it requires every policy to be `no-network`, rejects dynamic policies and custom Compose, and appends Harbor's native `docker-compose-no-network.yaml`. A retained probe container reported Docker `HostConfig.NetworkMode=none` before cleanup.

Oracle execution is a separate mode. The solution bundle must never coexist with a target-model agent session.

## Factory sandbox

Run generators, image builds, oracle checks, and known-bad verifier audits in isolated workers too. Generators have output quotas and no secret access. Image builds pin base-image digests before release and produce an SBOM plus vulnerability policy result. A build failure is an environment failure, never a model failure.

The local verifier audit remains a fast semantic gate. The 2026-07-23 Harbor batch additionally ran Oracle and the separate verifier in isolated Docker containers on all three remote hosts; both forms of evidence are required, and neither substitutes for target-model rollouts.
