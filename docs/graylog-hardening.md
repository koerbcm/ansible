# Graylog Hardening

This runbook captures the logging and storage lessons from the April 13, 2026 Graylog recovery on `docker1`.

Current manual stack reference:

- [graylog7.compose.reference.yml](/home/koerbcm/workspace/tools/ansiblePersonal/docs/examples/graylog7.compose.reference.yml)
- [graylog7.compose.local-storage.reference.yml](/home/koerbcm/workspace/tools/ansiblePersonal/docs/examples/graylog7.compose.local-storage.reference.yml)

This reference compose mirrors the live manual/Portainer-managed stack, including the currently published input ports. It is intentionally tracked in-repo even though Graylog is not yet managed by Ansible.

The local-storage reference compose shows the recommended post-migration shape: local bind mounts for live Graylog state on `docker1`, with the NAS still used as a backup target.

## Inputs and Port Separation

Graylog has two layers to keep straight:

- Docker `ports:` exposes host ports to the container.
- Graylog `Inputs` are the listeners that actually consume messages inside Graylog.

An exposed Docker port is not useful unless Graylog also has a matching input configured on that port.

Recommended port layout:

- `12202/udp`: Docker GELF for container logs
- `12201/udp`: general GELF if needed
- `1518/udp`: host/syslog forwarders
- `1514/udp`: pfSense syslog
- `1515/udp`: HAProxy syslog

Recommendations:

- Prefer GELF for managed Docker containers.
- Reserve syslog inputs for real syslog senders such as `rsyslog`, pfSense, and HAProxy.
- Avoid mixing host-forwarded syslog and container syslog-driver traffic on the same input when possible.
- Because Graylog on `docker1` is currently unmanaged by Ansible, any new published input ports must be added manually to the Graylog compose/runtime configuration.

Current repo direction:

- Managed `docker1` application containers should prefer GELF.
- Host forwarders such as `docker1` and `pi1` should target `1518/udp`.
- `pi1` keeps rsyslog/imfile only for SABnzbd file logs because that path adds value there.
- The reference Graylog compose publishes `1514/udp`, `1515/udp`, and `1518/udp` so Graylog inputs on those ports are actually reachable from the host network.

## Current Graylog Port Gaps

During recovery, these gaps were observed:

- Docker exposed `5140`, but Graylog initially had no matching input bound there.
- Graylog had local inputs on `1514` and `1515`, but those ports were not exposed by Docker.
- Docker exposed `5555`, `13301`, and `13302`, but no active matching inputs were verified during remediation.

Before relying on any Graylog port:

1. Verify the Docker port is published.
2. Verify a Graylog input exists on the same port and protocol.
3. Verify messages are visible in `All messages` for the correct time window.

For the recommended split above, add a dedicated Global Syslog UDP input on `1518` and publish `1518/udp` on the Graylog container host.

## DataNode Storage

The Graylog datanode failure was caused by corrupted OpenSearch shard data on NFS-backed storage.

Symptoms seen:

- `IndexNotFoundException`
- only `.nfs*` files present in shard directories
- datanode restart loop

The datanode volume was confirmed to be NFS-backed:

- `graylog7_graylog-datanode`
- `type: nfs`
- `device: :/volume1/graylog/datanode`

This is not a safe long-term placement for OpenSearch-style index data.

Recommended storage direction:

- move datanode storage to local disk on `docker1`
- strongly consider moving `graylog_data` local as well
- strongly consider moving MongoDB data local in the same maintenance window

Suggested local paths:

- `/srv/graylog/datanode`
- `/srv/graylog/graylog-data`
- `/srv/graylog/mongodb-data`
- `/srv/graylog/mongodb-config`

## Backup Model

The NAS should remain part of the design, but as a backup target rather than the live primary disk for Graylog state.

Recommended split:

- local primary storage on `docker1` for:
  - MongoDB data
  - Graylog server data
  - datanode/OpenSearch data
- NAS backup storage under `/mnt/backups/graylog` for:
  - MongoDB dumps
  - compose and `.env` backups
  - datanode snapshot repository contents

Why this is safer:

- MongoDB and datanode expect normal local filesystem semantics for live data.
- NFS is acceptable as a backup destination, but risky as the live datanode volume.
- This preserves a recovery path without recreating Graylog configuration from scratch.

Recommended backup targets:

- `/mnt/backups/graylog/mongo/`
- `/mnt/backups/graylog/config/`
- `/mnt/backups/graylog/opensearch-snapshots/`

Recommended backup approach:

- MongoDB:
  - nightly `mongodump` from `docker1` into `/mnt/backups/graylog/mongo/<date>/`
- Graylog compose and secrets:
  - copy the compose file, `.env`, and any helper scripts into `/mnt/backups/graylog/config/<date>/`
- datanode/OpenSearch:
  - use snapshots to a repository rooted at `/mnt/backups/graylog/opensearch-snapshots/`
  - when configuring the OpenSearch snapshot repository, use the path as seen from inside the datanode container, currently `/mnt/backups`
  - do not treat the live datanode directory as a normal file-copy backup source

For homelab recovery, MongoDB is the most important backup because it preserves users, streams, inputs, dashboards, and most Graylog configuration.

## Storage Migration Outline

Because Graylog on `docker1` is currently unmanaged by Ansible, treat this as a manual maintenance operation.

1. Create and verify local directories on `docker1`:
   - `/srv/graylog/mongodb-data`
   - `/srv/graylog/mongodb-config`
   - `/srv/graylog/graylog-data`
   - `/srv/graylog/datanode`
2. Back up the current compose, `.env`, and NFS-backed MongoDB/Graylog state.
3. Stop Graylog, datanode, and MongoDB.
4. Copy MongoDB and `graylog_data` from the NFS-backed volumes to the new local directories.
5. Do not copy the live datanode shard store back into place unless there is a specific reason to preserve it.
6. Update the compose file so MongoDB, Graylog, and datanode use local bind mounts.
7. Keep `/mnt/backups` mounted from the NAS and reserve it for backups and datanode snapshots.
8. Start MongoDB and verify it comes up cleanly.
9. Start datanode with an empty local data directory so it initializes clean local state.
10. Start Graylog.
11. Verify login, inputs, streams, and message ingestion.
12. After the stack is stable, add scheduled backup jobs from `docker1` to the NAS.

Because the datanode store was already reset during recovery, a fresh local datanode start is the simplest and safest approach.

## Migration Notes

Specific cautions for this stack:

- Keep MongoDB state if you want to preserve Graylog configuration.
- `graylog_data` is worth carrying forward because it contains Graylog local state such as the node id and journal-related files.
- Treat datanode as disposable runtime state unless you explicitly decide to preserve historical indices.
- If historical message retention matters later, prefer datanode snapshots to the NAS rather than a return to NFS-backed live storage.

## Post-Migration Checks

After switching to local storage, verify all of the following before calling the migration complete:

1. `docker ps` shows `mongodb`, `datanode`, and `graylog` healthy/stable.
2. Graylog UI is reachable on `http://10.27.70.11:9000/`.
3. Graylog can query the datanode successfully.
4. Existing Graylog users, streams, and inputs are still present.
5. Docker GELF messages arrive on `12202`.
6. Host/syslog-forwarded messages arrive on `1518`.
7. A fresh SABnzbd file-log marker from `pi1` appears in Graylog.
8. The datanode data path is now local, not NFS-backed.

## Long-Term Direction

Once the stack is stable on local storage, the next cleanup step should be to bring Graylog under Ansible management.

Recommended sequence:

1. Stabilize the live stack on local storage.
2. Confirm the backup jobs are working.
3. Promote the Graylog compose into an Ansible-managed role or stack template.
4. Remove the gap between repo reference and live runtime configuration.

## Recovery Note

The April 13, 2026 recovery restored service by:

1. stopping Graylog and datanode
2. backing up the NFS-backed datanode store
3. removing the live OpenSearch node data directory, including hidden `.nfs*` files
4. restarting datanode cleanly
5. restarting Graylog cleanly

That recovery restored service, but it does not remove the underlying NFS storage risk.
