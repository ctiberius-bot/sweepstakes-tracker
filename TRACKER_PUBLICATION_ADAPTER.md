# Tracker publication adapter contract

Signal Command is the system of record for discovery review. A tracker is the
system of record for its public inventory. The integration between them uses a
versioned manifest rather than tracker-specific database columns or HTML.

## Release flow

1. A reviewer completes the target tracker profile and every rating criterion
   in Signal Command.
2. Signal Command validates the candidate domain, recomputes the weighted
   rating server-side, and queues an immutable schema-v1 manifest.
3. The target tracker polls its protected queue. The Sweepstakes adapter runs
   every five minutes.
4. The tracker adapter validates the manifest again, maps it into its own
   canonical inventory, regenerates cards and detail pages, runs its native
   validation, and commits the generated release.
5. After the production-source push succeeds, the adapter acknowledges the
   public profile URL. Signal Command then shows the candidate as live.

Publication is idempotent by candidate ID and payload checksum. A changed
approved profile is republished; an unchanged manifest cannot create a
duplicate. Rejection or evidence requests cancel a queued release, while a
live profile must use the tracker's separate removal workflow.

## Reusing the workflow for another tracker

Every tracker reuses the envelope and transport fields:

- `schemaVersion`
- `target`, `pipeline`, and `candidateId`
- `name`, `domain`, `slug`, and `officialUrl`
- `profile` (owned by the target adapter)
- `rating` with scale metadata, weighted inputs, and evidence
- `publication` audit metadata

To add a tracker such as Subscription Boxes:

1. Add its adapter definition in Signal Command. Boxes already uses the five
   published subFactor criteria and a 1–5 lower-is-better scale.
2. Add a consumer that maps `profile` into that tracker's canonical service
   record. Do not copy the Sweepstakes record shape.
3. Run the tracker's existing build, tests, and deployment command.
4. Acknowledge the resulting public profile through the same protected API.

The Subscription Boxes production source is intentionally a Cloudflare Worker,
so its consumer should deploy through that existing Worker rather than through
the Sweepstakes GitHub/Pages release job.
