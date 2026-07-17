# Oracle Always Free Demo/Staging Runbook

This runbook provisions and operates the School Newsroom demo/staging environment manually. It is not a production design. It does not authorize paid resources, trial-only resources, a Pay As You Go upgrade, automatic deployment, or real data about minors.

The repository configuration uses this topology:

```text
Internet -> Caddy:80/443 -> Gunicorn web:8000 -> PostgreSQL:5432
                    |              |
                    |              +-- /srv/school-newsroom/media (read-write)
                    +-- /srv/school-newsroom/media (read-only)
```

Only Caddy publishes host ports. PostgreSQL and Gunicorn remain on private Compose networks. PostgreSQL uses the stable named volume `school_newsroom_staging_postgres_data`. Static assets are collected before Gunicorn starts and are served by WhiteNoise. Migrations, access bootstrap, site reconciliation, and user creation are deliberate operator actions, not container-restart side effects.

## Non-negotiable stop conditions

Stop without creating the resource or continuing the deployment if any of these conditions is true:

- the Oracle account has been upgraded to Pay As You Go;
- a resource is labeled paid, trial-only, or does not display the current **Always Free-eligible** label;
- the resource creation page does not show an estimated cost of USD 0;
- Compute is not being created in the tenancy home region;
- the selected shape, image, boot volume, block volume, public IP, VCN component, or other dependency is outside the currently available free allowance;
- Oracle reports no free host capacity after checking eligible availability domains or waiting for capacity;
- the only proposed workaround is an account upgrade, a paid shape, a paid load balancer, paid storage, or trial credit;
- the public hostname does not resolve to the VM or Caddy cannot obtain a browser-trusted certificate;
- any command would expose a real secret, token, password, private key, backup, or private information about a minor.

Do not share or use Wagtail Admin credentials over plain HTTP. Anonymous public smoke checks may be performed before HTTPS, but Admin access waits for valid HTTPS.

## Current facts and mandatory recheck

The following facts were reviewed on 2026-07-16. Oracle services, labels, limits, Console navigation, and third-party terms can change. Recheck the live Console labels and estimated cost immediately before selecting **Create** for every resource.

- Oracle's current [Always Free resources documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) says eligible resources display an **Always Free-eligible** label and Compute must be in the home region. It currently describes `VM.Standard.A1.Flex` and `VM.Standard.E2.1.Micro`, a combined free block/boot-volume allowance, and possible reclamation of idle instances. Do not copy numeric limits from this document into the Console; compare the current documentation, the tenancy's actual usage, the creation label, and the estimate.
- Oracle's [Free Tier documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm) distinguishes the expiring trial from Always Free. Trial credit is not an acceptable dependency for this environment.
- Oracle [Budgets](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm) are soft monitoring limits and alerts are evaluated periodically. A budget is **not** a spending cap and cannot replace resource-by-resource verification.
- The Console's [Limits, Quotas and Usage](https://docs.oracle.com/en-us/iaas/Content/General/service-limits/view-tenancy.htm) page shows the limits and usage currently assigned to the tenancy and region.
- Docker documents current [Ubuntu Engine installation](https://docs.docker.com/engine/install/ubuntu/) and supports both amd64 and arm64. The repository was validated locally only on x86_64; the selected Oracle architecture still needs a native build.
- Caddy requires a hostname resolving to the server and public ports 80/443 for normal [automatic HTTPS](https://caddyserver.com/docs/automatic-https) operation. Its [reverse proxy guide](https://caddyserver.com/docs/quick-starts/reverse-proxy) describes the same prerequisite.
- DuckDNS documents an HTTPS update API in its [official specification](https://www.duckdns.org/spec.jsp). Account availability and terms must be rechecked when the hostname is created.

## 1. Confirm account status and home region

1. Sign in to the OCI Console using the adult maintainer account.
2. Open the profile menu and record the tenancy name and displayed home region. Do not include OCIDs, email addresses, or account identifiers in repository files.
3. Open **Billing & Cost Management** -> **Cost Management** -> **Overview**. Also inspect the billing/account widget described in Oracle's [Viewing Billing Details](https://docs.oracle.com/en-us/iaas/Content/GSG/Concepts/console_topic-AccountCenter-Billing.htm) documentation.
4. Confirm the account is shown as **Always Free** or **Free Tier** and still presents an **Upgrade account** action rather than a Pay As You Go subscription. Do not select the upgrade action.
5. If a trial-credit balance is displayed, treat it as unavailable. Every resource in this runbook must independently show **Always Free-eligible** and USD 0 estimated cost.
6. Switch the Console to the home region and keep it there for Compute and storage creation.

Record the check date, account class shown, and home-region name in private operational evidence. Do not copy account numbers or personal data into Git.

## 2. Create and verify the staging compartment

Oracle's official procedure is [Creating a Compartment](https://docs.oracle.com/en-us/iaas/Content/Identity/compartments/To_create_a_compartment.htm).

1. Open **Identity & Security** -> **Identity** -> **Compartments**.
2. Select the tenancy root compartment.
3. Select **Create compartment**.
4. Use:

   ```text
   Name: school-newsroom-staging
   Description: Zero-cost demo/staging resources for School Newsroom
   Parent compartment: tenancy root
   ```

5. Do not place personal, school, minor, credential, or hostname data in names/tags.
6. Select **Create compartment**.
7. Reopen **Identity & Security** -> **Identity** -> **Compartments**, select `school-newsroom-staging`, and confirm it is active and its parent is correct.

All resources below must use this compartment. A resource found outside it is an operational warning and must be reviewed before continuing.

## 3. Configure a USD 1 monthly budget and alerts

This is an early-warning device, not a hard spending limit. Oracle says budget alerts are evaluated periodically, so charges can occur before an alert arrives.

1. Open **Billing & Cost Management** -> **Cost Management** -> **Budgets**.
2. Select **Create budget**.
3. Configure:

   ```text
   Scope: Compartment
   Target compartment: school-newsroom-staging
   Type: Recurring monthly budget
   Amount: USD 1.00
   Name: school-newsroom-staging-usd-1
   ```

4. Add an **Actual Spend** alert at 1% of the budget (USD 0.01) to an adult maintainer email.
5. Add a **Forecast Spend** alert at 1% of the budget to the same adult maintainer email.
6. Save the budget and both rules.
7. Reopen the budget details and confirm the compartment, amount, recipients, rule type, threshold, and active status.

If the Console rejects a 1% threshold, use the smallest allowed threshold and record it outside Git. See Oracle's [budget overview](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm) and [budget alert rule](https://docs.oracle.com/en-us/iaas/Content/Billing/Tasks/create-alert-rule.htm) documentation.

## 4. Inspect cost and tenancy limits before provisioning

### Cost Analysis

1. Open **Billing & Cost Management** -> **Cost Management** -> **Cost Analysis**.
2. Use the current month as the date range.
3. Add a **Compartment** filter for `school-newsroom-staging`.
4. Apply the query and confirm current cost is zero before resource creation.
5. Repeat this check after networking, Compute, storage, and deployment.

Follow Oracle's current [Cost Analysis](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costanalysisoverview.htm) documentation if the Console labels move.

### Limits, Quotas and Usage

1. Open **Governance & Administration** -> **Tenancy Management** -> **Limits, Quotas and Usage**.
2. Select the home region and the `school-newsroom-staging` compartment where the filter applies.
3. Inspect **Compute** limits/usage for the intended A1 and E2 shapes.
4. Inspect **Block Volume** limits/usage for combined boot and block storage.
5. Inspect public-IP/networking limits if shown.
6. Compare **Service Limit**, **Usage**, and **Available** with every existing tenancy resource, not just this project.

Stop if the required capacity is unavailable or the Console shows only trial/paid capacity. Do not request a paid limit increase.

## 5. Provision the minimal network

Do not create an OCI Load Balancer, NAT Gateway, Bastion, managed database, Object Storage bucket, or other unapproved service.

1. Open **Networking** -> **Virtual cloud networks**.
2. Select compartment `school-newsroom-staging` and **Create VCN**.
3. Create a VCN named `school-newsroom-staging-vcn` with IPv4 CIDR `10.0.0.0/16` and DNS resolution enabled.
4. Inside the VCN, create an Internet Gateway named `school-newsroom-staging-igw` only after verifying the current creation page shows zero estimated cost.
5. Open the VCN's **Security Lists** page and create a dedicated security list named `school-newsroom-staging-subnet`. Configure only these stateful rules:

   | Direction | Source/destination | Protocol | Type/code | Purpose |
   | --- | --- | --- | --- | --- |
   | Egress | destination `0.0.0.0/0` | All protocols | n/a | Required outbound package, image, DNS, time, DuckDNS, and ACME traffic |
   | Ingress | source `0.0.0.0/0` | ICMP | Type 3, code 4 | Path-MTU discovery: fragmentation needed with DF set |
   | Ingress | source `10.0.0.0/16` | ICMP | Type 3 | Essential destination-unreachable feedback inside the VCN |

   Do not add any TCP ingress rule to this security list, including the commonly preconfigured SSH rule. Do not copy the VCN default security list's complete rule set.
6. Create a regional public subnet named `school-newsroom-staging-public` with CIDR `10.0.1.0/24` and public IPv4 assignment allowed. Associate `school-newsroom-staging-subnet` as its **only** security list.
7. Reopen the subnet details and verify the associated security-list collection contains exactly `school-newsroom-staging-subnet`. The VCN default security list must not be associated with this subnet.
8. Add one route rule to the subnet route table:

   ```text
   Destination: 0.0.0.0/0
   Target type: Internet Gateway
   Target: school-newsroom-staging-igw
   ```

9. Create a Network Security Group named `school-newsroom-staging-web` for the VM VNIC.
10. Add TCP ingress only to this NSG, using exactly these stateful rules:

   | Source | Protocol | Destination port | Purpose |
   | --- | --- | --- | --- |
   | maintainer's current public CIDR | TCP | 22 | SSH; never use `0.0.0.0/0` when a stable maintainer CIDR is available |
   | `0.0.0.0/0` | TCP | 80 | HTTP redirect and ACME challenge |
   | `0.0.0.0/0` | TCP | 443 | public HTTPS |

11. Do not add duplicate TCP ingress to the subnet security list. The dedicated security list's stateful egress rule provides the required outbound access; keep the NSG focused on the three approved TCP ingress rules.
12. Before creating the VM, inspect both layers independently:

    - the subnet is associated only with `school-newsroom-staging-subnet`, not the VCN default security list;
    - the subnet security list contains no TCP ingress and only the required stateful egress and essential ICMP/path-MTU rules above;
    - every NSG intended for the VNIC is visible and reviewed;
    - `school-newsroom-staging-web` allows TCP 22 only from the maintainer's current CIDR and allows TCP 80/443 from `0.0.0.0/0`;
    - no subnet security list or VNIC NSG contains an unexpected rule for TCP 22, 8000, 5432, or 5434, the Docker API, or another service.

    Stop if either layer fails. In particular, a public or broader TCP 22 rule in any security list/NSG, or any ingress for 8000, 5432, or 5434, is a blocking configuration error.

OCI evaluates the union of the subnet security-list rules and all NSGs attached to the VNIC, so reviewing the NSG alone does not prove the ingress boundary. Oracle documents the public-subnet, Internet Gateway, public-IP, NSG/security-list, and guest-firewall layers in [Networking Security](https://docs.oracle.com/en-us/iaas/Content/Security/Reference/networking_security.htm).

## 6. Create the VM

1. Open **Compute** -> **Instances**.
2. Select compartment `school-newsroom-staging` and **Create instance**.
3. Use a generic name such as `school-newsroom-staging-web`.
4. Confirm the region shown is the tenancy home region.
5. Select an Ubuntu LTS image that the live Console labels **Always Free-eligible** and shows no licensing charge. The commands below assume Ubuntu 24.04; if another version is selected, use Docker's official instructions for that exact supported version.
6. Prefer `VM.Standard.A1.Flex`. Allocate only OCPUs/memory currently shown within the tenancy's remaining Always Free allowance. Do not rely on remembered numeric limits.
7. Use `VM.Standard.E2.1.Micro` only if A1 has no capacity and the full stack later passes native build, memory, persistence, and UAT. One GB may be inadequate; a successful VM creation is not proof of application suitability.
8. Use **On-demand capacity** only. Do not select capacity reservations, dedicated hosts, or paid options.
9. Select the VCN, public subnet, and `school-newsroom-staging-web` NSG created above. Before continuing, inspect the subnet's associated security lists and every NSG attached to the VNIC again; confirm the dedicated security list is the subnet's only list and that the VCN default security list is absent. Assign a public IPv4 address only after its current cost/eligibility is verified.
10. Add only the maintainer's SSH **public** key. Never upload or commit a private key.
11. Select the smallest boot volume that the live Console labels eligible and that leaves enough free combined volume capacity for the separate data volume. Do not enable paid performance, paid backup, or custom encryption services.
12. Before selecting **Create**, inspect the summary for:

    - **Always Free-eligible** on shape and image;
    - home region;
    - correct compartment;
    - approved OCPU/memory and volume size;
    - USD 0 estimated cost;
    - no trial-only or paid component.

13. Select **Create** only when every item passes.

Oracle's current [Creating an Instance](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm) procedure is authoritative. If Oracle reports **Out of host capacity**, try another eligible availability domain where offered or wait. Do not upgrade the account or select a paid shape.

## 7. Create, attach, and mount persistent storage by UUID

Use a separate block volume for `/srv/school-newsroom` only if its live creation page displays **Always Free-eligible**, the tenancy has free combined capacity after the boot volume, and estimated cost is USD 0. Otherwise stop and report; do not create paid storage.

1. Open **Storage** -> **Block Storage** -> **Block Volumes**.
2. Select compartment `school-newsroom-staging`, then **Create block volume**.
3. Use name `school-newsroom-staging-data`, the VM's availability domain, and the smallest currently allowed size/performance that remains within the free allowance.
4. Verify the eligibility label and USD 0 estimate before selecting **Create**.
5. Open **Compute** -> **Instances** -> `school-newsroom-staging-web` -> **Resources** -> **Attached block volumes** -> **Attach block volume**.
6. Select the volume, use a supported paravirtualized attachment, read/write access, and a consistent device path if the shape offers one.
7. Connect by SSH and identify the new empty device. The following commands are destructive if the wrong device is selected:

   ```bash
   lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS
   sudo blkid
   ```

8. Set `DATA_DEVICE` only after comparing the Console attachment with `lsblk`. Enter the complete `/dev/...` path of the verified empty staging device:

   ```bash
   read -r -p "Verified empty staging block device: " DATA_DEVICE
   case "$DATA_DEVICE" in
       /dev/*) ;;
       *) echo "STOP: expected a complete /dev/... path." >&2; exit 1 ;;
   esac
   test -b "$DATA_DEVICE" || { echo "STOP: not a block device." >&2; exit 1; }
   sudo file -s "$DATA_DEVICE"
   ```

9. **Stop if the device has a filesystem or data.** Format only a newly created, verified empty staging volume:

   ```bash
   sudo mkfs.ext4 -L school-newsroom-staging "$DATA_DEVICE"
   DATA_UUID="$(sudo blkid -s UUID -o value "$DATA_DEVICE")"
   test -n "$DATA_UUID"
   sudo install -d -m 0755 /srv/school-newsroom
   printf 'UUID=%s /srv/school-newsroom ext4 defaults,_netdev,nofail 0 2\n' "$DATA_UUID" | sudo tee -a /etc/fstab >/dev/null
   sudo mount -a
   findmnt /srv/school-newsroom
   ```

10. Confirm the mounted UUID matches the new volume:

    ```bash
    findmnt -no UUID,SOURCE,FSTYPE,OPTIONS /srv/school-newsroom
    df -h /srv/school-newsroom
    ```

Oracle recommends UUIDs because device ordering can change and documents `_netdev`/`nofail` in [Traditional fstab Options](https://docs.oracle.com/en-us/iaas/Content/Block/References/fstaboptions.htm). Also review [Creating a Block Volume](https://docs.oracle.com/en-us/iaas/Content/Block/Tasks/creatingavolume.htm) and [Attaching a Block Volume](https://docs.oracle.com/iaas/Content/Block/Tasks/attachingavolume.htm).

Do not claim reboot persistence until the maintainer performs a real reboot and verifies `findmnt`, Docker, database, media, and HTTPS afterward.

## 8. Prepare host directories and firewall

The application image uses UID/GID 10001. Caddy reads public media; the web process writes it.

```bash
sudo install -d -m 0755 /srv/school-newsroom
sudo install -d -m 0755 -o 10001 -g 10001 /srv/school-newsroom/media
sudo install -d -m 0700 -o "$(id -u)" -g "$(id -g)" /srv/school-newsroom/backups
sudo install -d -m 0750 /etc/school-newsroom
```

Configure the Ubuntu firewall. Enter the maintainer's actual public CIDR when prompted; do not store it in Git:

```bash
sudo apt-get update
sudo apt-get install -y ufw ca-certificates curl git dnsutils
sudo ufw default deny incoming
sudo ufw default allow outgoing
read -r -p "Maintainer public CIDR allowed for SSH: " MAINTAINER_PUBLIC_CIDR
test -n "$MAINTAINER_PUBLIC_CIDR"
sudo ufw allow from "$MAINTAINER_PUBLIC_CIDR" to any port 22 proto tcp
unset MAINTAINER_PUBLIC_CIDR
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status numbered
```

Docker warns that published container ports can bypass UFW rules. This staging Compose file publishes only Caddy's 80/443; database and web have no published ports. Treat the dedicated subnet security list and every VNIC NSG as a combined OCI boundary, keep UFW as the guest boundary, and recheck both OCI rule collections plus published ports after every network or Compose change.

## 9. Install Docker Engine and Compose

Use Docker's signed Ubuntu apt repository, not the convenience script. Recheck [Docker's official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/) before running these commands:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
```

Using the `docker` group grants root-equivalent host control. This runbook keeps `sudo docker` explicit instead of adding broad group membership.

## 10. Configure DuckDNS without exposing the token

1. Open [DuckDNS](https://www.duckdns.org/) in the maintainer's browser.
2. Sign in with an adult maintainer identity. Do not use a student/minor identity.
3. Create a generic subdomain that contains no personal or confidential school information.
4. Record the resulting `<subdomain>.duckdns.org` hostname in the private deployment record.
5. Treat the account token as a password. Never place it in Git, Compose, feedback, tickets, screenshots, command arguments, shell history values, or logs.

Create a root-readable curl configuration interactively. The entered token is not part of the command history and is passed to `tee` on standard input, not as a process argument:

```bash
read -r -p "DuckDNS subdomain without .duckdns.org: " DUCKDNS_DOMAIN
read -r -s -p "DuckDNS token: " DUCKDNS_TOKEN
printf '\n'
sudo install -m 0600 /dev/null /etc/school-newsroom/duckdns.curl
{
    printf 'url = "https://www.duckdns.org/update"\n'
    printf 'get\n'
    printf 'data-urlencode = "domains=%s"\n' "$DUCKDNS_DOMAIN"
    printf 'data-urlencode = "token=%s"\n' "$DUCKDNS_TOKEN"
    printf 'data-urlencode = "ip="\n'
    printf 'fail\nsilent\nshow-error\n'
} | sudo tee /etc/school-newsroom/duckdns.curl >/dev/null
unset DUCKDNS_TOKEN
unset DUCKDNS_DOMAIN
sudo chmod 0600 /etc/school-newsroom/duckdns.curl
sudo stat -c '%a %U:%G %n' /etc/school-newsroom/duckdns.curl
```

Install a quiet updater that never prints the request, token, or successful response:

```bash
sudo tee /usr/local/sbin/school-newsroom-duckdns-update >/dev/null <<'EOF'
#!/bin/sh
set -eu

response="$(curl --config /etc/school-newsroom/duckdns.curl)"
if [ "$response" != "OK" ]; then
    echo "DuckDNS update failed." >&2
    exit 1
fi
EOF
sudo chmod 0755 /usr/local/sbin/school-newsroom-duckdns-update

sudo tee /etc/systemd/system/school-newsroom-duckdns.service >/dev/null <<'EOF'
[Unit]
Description=Update the School Newsroom staging DuckDNS address
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/school-newsroom-duckdns-update
PrivateTmp=true
NoNewPrivileges=true
EOF

sudo tee /etc/systemd/system/school-newsroom-duckdns.timer >/dev/null <<'EOF'
[Unit]
Description=Periodically update the School Newsroom staging DuckDNS address

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now school-newsroom-duckdns.timer
sudo systemctl start school-newsroom-duckdns.service
sudo systemctl status --no-pager school-newsroom-duckdns.service
sudo systemctl list-timers --all school-newsroom-duckdns.timer
```

The official DuckDNS specification recommends HTTPS for updates. Never use the HTTP API. If the updater fails, inspect only the generic service exit status; do not add shell tracing or print the curl config.

## 11. Clone an approved repository revision

Use an adult maintainer-controlled deploy account. Replace placeholders locally; do not commit them.

```bash
sudo install -d -m 0755 -o "$(id -u)" -g "$(id -g)" /opt/school-newsroom
read -r -p "Approved repository URL (without embedded credentials): " APPROVED_REPOSITORY_URL
test -n "$APPROVED_REPOSITORY_URL"
git clone "$APPROVED_REPOSITORY_URL" /opt/school-newsroom
cd /opt/school-newsroom
git fetch --prune
read -r -p "Approved commit SHA: " APPROVED_COMMIT_SHA
git rev-parse --verify "${APPROVED_COMMIT_SHA}^{commit}"
git checkout --detach "$APPROVED_COMMIT_SHA"
git status --short --branch
git rev-parse HEAD
unset APPROVED_REPOSITORY_URL
unset APPROVED_COMMIT_SHA
```

Deploy an immutable reviewed commit SHA. Do not configure automatic pulls from `main`, a `staging` branch, or GitHub Actions in EPIC8-001. If the repository is private, use a narrowly scoped deploy credential outside the clone and follow the hosting provider's secret guidance; never commit it.

## 12. Create the real staging environment without printing secrets

Install the safe template outside Git, then edit it with `sudoedit`:

```bash
cd /opt/school-newsroom
sudo install -m 0600 docker/staging/staging.env.example /etc/school-newsroom/staging.env
sudoedit /etc/school-newsroom/staging.env
sudo chmod 0600 /etc/school-newsroom/staging.env
sudo stat -c '%a %U:%G %n' /etc/school-newsroom/staging.env
```

Replace every `.invalid` hostname/email and every `replace-with-...` value inside the editor. Use a password manager to create unique values and paste them into `sudoedit`; do not generate or echo them in shell commands. The database password appears in both `POSTGRES_PASSWORD` and URL-encoded form in `DATABASE_URL`.

Required invariants:

```text
DJANGO_SETTINGS_MODULE is fixed by Compose to config.settings.production
DJANGO_ALLOWED_HOSTS=<subdomain>.duckdns.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://<subdomain>.duckdns.org
DJANGO_WAGTAILADMIN_BASE_URL=https://<subdomain>.duckdns.org
DJANGO_LOG_LEVEL=INFO
DJANGO_SECURE_SSL_REDIRECT=true
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=false
DJANGO_SECURE_HSTS_PRELOAD=false
SEO_DEFAULT_NOINDEX=true
DATABASE_URL uses host db and port 5432
```

Verify that every pass-through secret is present and non-empty without printing any value:

```bash
required_secret_names="DATABASE_URL DJANGO_SECRET_KEY POSTGRES_PASSWORD"
for name in $required_secret_names; do
    if ! sudo grep -Eq "^${name}=.+$" /etc/school-newsroom/staging.env; then
        echo "STOP: ${name} is missing or empty in staging.env." >&2
        exit 1
    fi
done
unset required_secret_names
unset name
```

The mandatory `--env-file /etc/school-newsroom/staging.env` resolves these pass-through values into their service environments. When a source value is unavailable, Compose leaves the pass-through entry unresolved with no value to inject, so this preflight is the operator's fail-closed deployment guard and prints only a missing variable's name. Production settings also reject missing `DATABASE_URL` and `DJANGO_SECRET_KEY`; on a new database volume, the official PostgreSQL image refuses normal initialization without its required `POSTGRES_PASSWORD`. No secret value is printed by this check.

Check for unmodified placeholders without displaying the file:

```bash
if sudo grep -Eq 'replace-with-|example\.invalid' /etc/school-newsroom/staging.env; then
    echo "STOP: staging.env still contains safe-template placeholders." >&2
    exit 1
fi
```

Do not run `docker compose config` without output filtering against the real environment because expanded output contains secrets. Syntax-check it quietly:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml config --quiet
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml config --services
```

Expected services are `db`, `web`, and `proxy`. Repository review must confirm only `proxy` has `ports`; `db` and `web` use internal networks/exposure only.

## 13. First manual deployment

DNS must already resolve to the VM before Caddy can obtain the normal public certificate. Confirm the hostname privately from `staging.env`, then use `dig` without printing any other environment value:

```bash
STAGING_HOSTNAME="$(sudo sed -n 's/^STAGING_HOSTNAME=//p' /etc/school-newsroom/staging.env)"
test -n "$STAGING_HOSTNAME"
dig +short "$STAGING_HOSTNAME" A
unset STAGING_HOSTNAME
```

Build natively on the VM and start only PostgreSQL first:

```bash
cd /opt/school-newsroom
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml build --pull web
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d db
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml ps
```

Apply migrations explicitly:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py migrate --noinput
```

If migration `0009_reconcile_mvp_access` stops because `Moderadores` or `Editores` has users or an unexpected dependency, stop. Reconcile those accounts/dependencies deliberately; never delete access history blindly.

Run access bootstrap twice and confirm idempotency:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py bootstrap_mvp_access
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py bootstrap_mvp_access
```

Reconcile the database-backed Wagtail Site hostname and HTTPS port:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py shell -c 'import os; from wagtail.models import Site; site = Site.objects.get(is_default_site=True); site.hostname = os.environ["STAGING_HOSTNAME"]; site.port = 443; site.save(update_fields=["hostname", "port"]); print(f"Default Wagtail Site: {site.hostname}:{site.port}")'
```

Create the technical superuser only if one does not exist. The command prompts privately; do not pass a password argument:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py createsuperuser
```

Start the complete stack:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml ps
```

The web startup runs `collectstatic` and Gunicorn only. It does not migrate, bootstrap permissions, or create users.

## 14. HTTPS and public smoke verification

Set only the non-secret hostname variable:

```bash
STAGING_HOSTNAME="$(sudo sed -n 's/^STAGING_HOSTNAME=//p' /etc/school-newsroom/staging.env)"
test -n "$STAGING_HOSTNAME"
dig +short "$STAGING_HOSTNAME" A
curl --head --max-time 15 "http://${STAGING_HOSTNAME}/"
curl --fail --head --max-time 15 "https://${STAGING_HOSTNAME}/"
curl --fail --head --max-time 15 "https://${STAGING_HOSTNAME}/noticias/"
curl --head --max-time 15 "https://${STAGING_HOSTNAME}/admin/"
openssl s_client -connect "${STAGING_HOSTNAME}:443" -servername "$STAGING_HOSTNAME" </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
unset STAGING_HOSTNAME
```

Expected evidence:

- HTTP redirects to the same hostname over HTTPS.
- HTTPS presents a browser-trusted certificate for the exact hostname.
- Home and `/noticias/` respond without a certificate error.
- `/admin/` redirects to the HTTPS login path.

If any item fails, do not share or use Admin credentials over the Internet. Review DNS, NSG, UFW, ports 80/443, Caddy logs, and the DuckDNS updater without printing secrets.

## 15. Create nominal adult users through HTTPS Admin

After valid HTTPS is confirmed, sign in as the technical superuser:

```text
https://<staging-hostname>/admin/
```

Create separate adult accounts through **Configuración** -> **Usuarios** -> **Añadir un usuario**:

- one active, non-superuser account assigned only to `Director/editor`;
- one active, non-superuser account assigned only to `Curador SEO`.

Use nominal adult identity data approved for the demo. Do not create accounts for students, minors, teachers/monitors, or parents. Enter unique temporary passwords only in the HTTPS form, deliver them privately, and require an immediate voluntary change through **Cuenta** -> **Cambiar contraseña**. The MVP does not technically force first-login password change.

Do not use a superuser to demonstrate role isolation. Do not store usernames with passwords in scripts, Git, tickets, screenshots, or UAT evidence.

## 16. Start, stop, restart, and update

Define no aliases that print or export the environment. Run explicit commands from `/opt/school-newsroom`.

```bash
# Status
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml ps

# Start/reconcile containers
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d

# Stop containers while preserving volumes and media
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml stop

# Start stopped containers
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml start

# Restart only Caddy
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml restart proxy

# Remove containers/networks while preserving named volumes
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml down
```

Never use `down -v`, `docker volume rm`, or delete `/srv/school-newsroom/media` during normal operation.

For a manual code update:

1. Run the database/media backup procedure below.
2. Fetch and check out an explicitly approved commit.
3. Review status and commit SHA.
4. Build, migrate, bootstrap, reconcile the Wagtail Site, and start:

```bash
cd /opt/school-newsroom
git fetch --prune
read -r -p "New approved commit SHA: " NEW_APPROVED_COMMIT_SHA
git rev-parse --verify "${NEW_APPROVED_COMMIT_SHA}^{commit}"
git checkout --detach "$NEW_APPROVED_COMMIT_SHA"
git status --short --branch
git rev-parse HEAD
unset NEW_APPROVED_COMMIT_SHA
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml build --pull web
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py migrate --noinput
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py bootstrap_mvp_access
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py shell -c 'import os; from wagtail.models import Site; site = Site.objects.get(is_default_site=True); site.hostname = os.environ["STAGING_HOSTNAME"]; site.port = 443; site.save(update_fields=["hostname", "port"]); print(f"Default Wagtail Site: {site.hostname}:{site.port}")'
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d
```

This is manual deployment. Do not add a GitHub deployment workflow or automatically follow `main` in this ticket.

## 17. Logs and operational inspection

The staging Compose file explicitly uses Docker's `json-file` driver for `proxy`, `web`, and `db`, with `max-size=10m` and `max-file=3`. Rotation bounds each service container's Docker JSON logs instead of allowing one unbounded file. A recreated container receives the same Compose policy.

Verify the effective container policy without printing container environments or expanded Compose configuration:

```bash
cd /opt/school-newsroom
for service in proxy web db; do
    container_id="$(sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml ps -q "$service")"
    test -n "$container_id" || { echo "STOP: ${service} has no running container." >&2; exit 1; }
    sudo docker inspect --format '{{.Name}} driver={{.HostConfig.LogConfig.Type}} max-size={{index .HostConfig.LogConfig.Config "max-size"}} max-file={{index .HostConfig.LogConfig.Config "max-file"}}' "$container_id"
done
unset container_id
```

Each line must report `driver=json-file max-size=10m max-file=3`. Stop if any service differs. This format selects only the container name and log configuration; do not replace it with an unrestricted `docker inspect` or a command that prints environments.

Use bounded application log reads:

```bash
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml logs --tail=100 proxy
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml logs --tail=100 web
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml logs --tail=100 db
sudo journalctl -u school-newsroom-duckdns.service --since today --no-pager
```

Review for errors, stack traces, unexpected request data, passwords, tokens, environment dumps, and private information about minors. Caddy access logs include network/request metadata. Systemd journal retention applies to host services such as `school-newsroom-duckdns.service`; it does not bound Docker's `json-file` logs, which are controlled by the Compose rotation settings above. Keep host journal retention minimal and appropriate for a demo, and do not add debug logging in staging.

## 18. Persistence checks

Use only fictional/non-sensitive news and image data. Record the page URL, database-visible title, and media URL before each action.

1. Create or edit a fictional news page with a fictional image through HTTPS as `Director/editor`.
2. Restart web and verify page and image:

   ```bash
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml restart web
   ```

3. Restart Caddy and verify again:

   ```bash
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml restart proxy
   ```

4. Restart PostgreSQL, wait for healthy status, and verify again:

   ```bash
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml restart db
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml ps
   ```

5. Rebuild/redeploy the same approved commit without `-v` and verify again:

   ```bash
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d --build
   ```

6. Verify the image file exists below `/srv/school-newsroom/media` and is owned by UID/GID 10001 without printing private filenames into shared evidence:

   ```bash
   sudo find /srv/school-newsroom/media -xdev -printf '%U:%G %m %y\n' | sort -u
   ```

7. A real VM reboot check is separate maintainer validation. After reboot, confirm `findmnt`, Docker services, Compose health, public HTTPS, page data, and media before marking it passed.

## 19. Manual backup

Back up before every code/config/migration change. Backups contain private database data and must stay mode 0600 in the mode-0700 backup directory. A same-volume backup protects against operator error only; copy it to an adult maintainer-controlled encrypted destination if policy permits and that destination has verified zero cost.

Use a short maintenance window so the database and media archive are coherent:

```bash
cd /opt/school-newsroom
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml stop proxy web
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml exec -T db sh -c 'pg_dump --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --format=custom' > "/srv/school-newsroom/backups/database-${timestamp}.dump"
tar --create --gzip --file "/srv/school-newsroom/backups/media-${timestamp}.tar.gz" --directory /srv/school-newsroom media
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml exec -T db pg_restore --list < "/srv/school-newsroom/backups/database-${timestamp}.dump" >/dev/null
tar --list --gzip --file "/srv/school-newsroom/backups/media-${timestamp}.tar.gz" >/dev/null
sha256sum "/srv/school-newsroom/backups/database-${timestamp}.dump" "/srv/school-newsroom/backups/media-${timestamp}.tar.gz" > "/srv/school-newsroom/backups/checksums-${timestamp}.txt"
chmod 0600 "/srv/school-newsroom/backups/database-${timestamp}.dump" "/srv/school-newsroom/backups/media-${timestamp}.tar.gz" "/srv/school-newsroom/backups/checksums-${timestamp}.txt"
sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml start web proxy
```

Confirm non-zero sizes and restrictive modes without printing contents:

```bash
stat -c '%a %U:%G %s %n' "/srv/school-newsroom/backups/database-${timestamp}.dump" "/srv/school-newsroom/backups/media-${timestamp}.tar.gz" "/srv/school-newsroom/backups/checksums-${timestamp}.txt"
```

Do not put backups in the repository, media directory, Caddy mount, Object Storage, or public file shares.

## 20. Basic restore procedure

Restore is destructive. EPIC8-001 documents the procedure; a formal restore drill belongs to EPIC8-003. Never test it against the maintainer's persistent database without an explicit maintenance decision and verified current backups.

1. Confirm the target is demo/staging, not production.
2. Confirm the selected database dump and media archive are a matching pair and pass their checksums/list commands.
3. Record the current approved commit and create one more backup.
4. Stop public/application writes:

   ```bash
   cd /opt/school-newsroom
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml stop proxy web
   ```

5. Preserve the current media tree instead of deleting it:

   ```bash
   restore_timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
   sudo mv /srv/school-newsroom/media "/srv/school-newsroom/media-before-restore-${restore_timestamp}"
   sudo install -d -m 0755 -o 10001 -g 10001 /srv/school-newsroom/media
   ```

6. Recreate only the confirmed staging database and restore the dump:

   ```bash
   read -r -p "Confirmed database dump basename: " DATABASE_DUMP_NAME
   case "$DATABASE_DUMP_NAME" in
       "" | */*) echo "STOP: enter a basename from the backup directory." >&2; exit 1 ;;
   esac
   DATABASE_DUMP="/srv/school-newsroom/backups/${DATABASE_DUMP_NAME}"
   test -f "$DATABASE_DUMP"
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml exec -T db sh -c 'dropdb --force --if-exists --username "$POSTGRES_USER" "$POSTGRES_DB" && createdb --username "$POSTGRES_USER" "$POSTGRES_DB"'
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml exec -T db sh -c 'pg_restore --exit-on-error --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB"' < "$DATABASE_DUMP"
   unset DATABASE_DUMP_NAME
   unset DATABASE_DUMP
   ```

7. Extract the matching media archive, restore ownership/modes, and do not follow unreviewed archive paths:

   ```bash
   read -r -p "Confirmed media archive basename: " MEDIA_ARCHIVE_NAME
   case "$MEDIA_ARCHIVE_NAME" in
       "" | */*) echo "STOP: enter a basename from the backup directory." >&2; exit 1 ;;
   esac
   MEDIA_ARCHIVE="/srv/school-newsroom/backups/${MEDIA_ARCHIVE_NAME}"
   test -f "$MEDIA_ARCHIVE"
   tar --list --gzip --file "$MEDIA_ARCHIVE"
   sudo tar --extract --gzip --file "$MEDIA_ARCHIVE" --directory /srv/school-newsroom
   unset MEDIA_ARCHIVE_NAME
   unset MEDIA_ARCHIVE
   sudo chown -R 10001:10001 /srv/school-newsroom/media
   sudo find /srv/school-newsroom/media -type d -exec chmod 0755 {} +
   sudo find /srv/school-newsroom/media -type f -exec chmod 0644 {} +
   ```

8. Apply forward migrations, reconcile owned access, and restore the current hostname:

   ```bash
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py migrate --noinput
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py bootstrap_mvp_access
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml run --rm web python manage.py shell -c 'import os; from wagtail.models import Site; site = Site.objects.get(is_default_site=True); site.hostname = os.environ["STAGING_HOSTNAME"]; site.port = 443; site.save(update_fields=["hostname", "port"]); print(f"Default Wagtail Site: {site.hostname}:{site.port}")'
   sudo docker compose --env-file /etc/school-newsroom/staging.env -f docker-compose.staging.yml up -d
   ```

9. Run HTTPS, page, role, workflow, privacy, and media smoke checks before removing the preserved pre-restore media tree. Its removal is a later explicit maintenance action, not part of restore.

## 21. Deactivate an adult user's access

Through valid HTTPS as the technical superuser:

1. Open **Configuración** -> **Usuarios**.
2. Select the adult user.
3. Clear **Activo** and save.
4. Confirm the account can no longer sign in.
5. Preserve the user record so editorial/workflow history remains attributable.

To change roles without deactivation, change only the **Grupos** selection. Do not grant individual permissions or delete the owned groups.

## 22. Periodic zero-cost and activity review

Perform this review at least weekly during active UAT and monthly while the environment remains available:

1. **Billing & Cost Management** -> **Cost Management** -> **Budgets**: confirm the USD 1 budget and alert rules are active.
2. **Billing & Cost Management** -> **Cost Management** -> **Cost Analysis**: filter to `school-newsroom-staging`, current month, and confirm zero cost.
3. **Governance & Administration** -> **Tenancy Management** -> **Limits, Quotas and Usage**: review Compute, block/boot storage, and public-IP usage in the home region.
4. **Compute** -> **Instances** -> `school-newsroom-staging-web` -> **Metrics**: review CPU, memory where available, and network activity. Oracle's Always Free documentation currently warns that idle instances may be reclaimed; recheck the current policy rather than generating artificial traffic.
5. **Storage** -> **Block Storage** -> **Block Volumes**: confirm only the intended eligible volumes/backups exist.
6. **Networking** -> **Virtual cloud networks**: inspect the subnet's associated security lists and every NSG attached to the VNIC. Confirm only the dedicated `school-newsroom-staging-subnet` list is associated, the VCN default security list is absent, and neither layer contains unexpected ingress.
7. Review the DuckDNS timer, certificate dates, disk space, Compose status, and bounded logs. Repeat the targeted `docker compose ps -q` plus `docker inspect` logging check for all three services.
8. Remove unused adult access promptly and deactivate the environment when it is no longer required. Never create artificial activity solely to evade provider policy.

Any non-zero cost, unexpected resource, eligibility-label change, capacity warning, or account-status change is a stop-and-investigate event. A budget alert is evidence to investigate, not proof that spending was blocked.

## 23. Acceptance evidence boundary

Repository-local validation can establish settings, Compose shape, x86_64 build, non-root execution, static collection, disposable migrations/bootstrap, and fictional media routing. It cannot establish:

- current Oracle A1/AMD capacity or native ARM64 success;
- real OCI labels, estimates, cost, public IP, subnet security-list/NSG union, UFW, or mounted-volume reboot persistence;
- real DuckDNS account behavior, DNS propagation, certificate issuance/renewal, or Internet HTTPS;
- real backup generation on Oracle storage;
- browser-based public/editorial UAT.

Record those items as pending until the maintainer actually performs them. Use [Oracle staging UAT](oracle_staging_uat.md) for evidence, and use [Wagtail MVP Access Runbook](wagtail_access_mvp.md) for the canonical role/workflow procedure.
