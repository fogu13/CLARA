# Production API outage, 15 September 2026: record

Recorded from the owner's terminal output on the VPS and from the GitHub Actions uptime runs; kept here because the thesis dates its deployment claims against it (Appendix G.8).

## Timeline (UTC)

- **08:07:01** The API's last database connection through the Supabase session pooler closes (`ClientHandler: Terminate received from client`); the pooler pool shuts down at 08:07:57 for lack of subscribers. No connection from the API is seen afterwards (Supabase `supavisor_logs`). The API had connected every 30 minutes through the night.
- **07:12–07:14** Scheduled uptime run 881 still passes 21 of 22 checks: `/health` 200; only `/ready` 404 (the running image predates the readiness route).
- **12:47–12:48** Scheduled uptime run 882: TLS, security headers and the unauthenticated 401 on `/problems` still answer, then `/health` times out after 15 s on both attempts. The process was accepting connections but no longer serving requests that need a worker thread.
- **13:54** Owner runs `docker compose ps` (container `clara-api`, image `clara-clara-api`, **created 3 weeks ago, up 3 weeks**, no health status because the image predates the `HEALTHCHECK`) and `docker compose restart clara-api`.
- **13:56, 13:58** Uptime runs 883 and 884: every API route returns 502 from Caddy; the container is in a restart loop. Container logs: `psycopg_pool.PoolTimeout: couldn't get a connection after 15.00 sec` and `failed to resolve host 'aws-1-eu-central-1.pooler.supabase.com': [Errno -3] Temporary failure in name resolution` at boot (the rule store connects during app creation).
- **Diagnosis on the host:** `getent hosts` returns nothing for the pooler hostname; `resolvectl query` fails ("All attempts to contact name servers or networks failed", later "Query timed out"); IPv4 and IPv6 reach Cloudflare and Hetzner resolvers; a raw UDP DNS query from Python to 185.12.64.1, 185.12.64.2 and 1.1.1.1 answers with four records each. `resolvectl status` shows the Tailscale link (`tailscale0`) with DNS servers 100.100.100.100 and fd7a:115c:a1e0::53, DNS domain `~.` and default route yes: Tailscale's MagicDNS was routing every lookup and had stopped answering. Disk 55% used, memory fine.
- **Fix:** drop-in `/etc/systemd/resolved.conf.d/ipv4-upstream.conf` with `DNS=185.12.64.1 185.12.64.2 1.1.1.1` and `Domains=~.`, `systemctl restart systemd-resolved`; the query resolves via `eth0`. The container's restart loop then succeeds on its own.
- **14:14:28** The API authenticates to the pooler again (`Starting pool(s)`).
- **14:16** Uptime run 886: 21 of 22 checks pass; the only failure is the pre-existing `/ready` 404.

## What the record establishes for the thesis

1. The API image serving production on 15 September 2026 was created about three weeks earlier (last week of August 2026). Its commit is not recorded because the image carried no build identity (`/health` reported no version). It therefore predates every commit from 2 September onward, including the readiness route (01ced20), identifier redaction at the model boundary (4bd1af8), migrations 013–017 and the September governance and measurement changes. Those mechanisms were implemented and regression-tested at their commits and were not deployed at the time of writing.
2. The outage was a host DNS failure (Tailscale MagicDNS owning all lookups), not an application defect; the application's contribution was that dead database sockets froze the worker pool without a timeout, and that a boot-time database connection failure crash-loops rather than degrades.
3. The uptime workflow had been red since 2 September because of the `/ready` 404 (issue #141), so it could not distinguish a version lag from an outage.

## Follow-ups (owner)

- Stop Tailscale from owning DNS on the VPS (`tailscale set --accept-dns=false`) or fix the tailnet DNS settings.
- Deploy the current image with `--build-arg GIT_COMMIT` so `/health` reports the served commit and `/ready` exists.
- Application hardening: TCP keepalives and a read timeout on database connections; restart-on-unhealthy for the container.
