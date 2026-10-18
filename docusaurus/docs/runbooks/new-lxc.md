# Runbook: Create a New LXC

End-to-end procedure for provisioning a new Docker host LXC with Terraform and
configuring it with Ansible. This is the infrastructure half of standing up a
service; for the service/compose side see the
[new service runbook](./new-service.md).

Run all commands from the repo root unless noted.

## Pick the tier and addressing

Each tier is its own Terraform env and `/24`. Node is picked per-module
(each `module` block sets its own `node_name`): `core` is entirely on node1,
but `prod` and `test` are each split across two nodes today:

| Tier   | Env dir               | Subnet        | Node(s) in use today                                |
| ------ | --------------------- | ------------- | --------------------------------------------------- |
| `core` | `terraform/envs/core` | `10.0.1.0/24` | node1 (all of it)                                   |
| `prod` | `terraform/envs/prod` | `10.0.2.0/24` | node1 (immich, nextcloud, searxng), node3 (coolify) |
| `test` | `terraform/envs/test` | `10.0.3.0/24` | node1 (n8n), node2 (internship-watcher, kafka)      |

Check [`docusaurus/docs/network.md`](../network.md) (the authoritative
topology reference) for current per-node capacity before picking which node
a new module targets. Pick an unused `vm_id` and IP within the tier's subnet.
The gateway is `10.0.0.1` and all LXC IPs use a `/22` mask.

## 1. Add a Terraform module block

Append a `module` block to `terraform/envs/<tier>/main.tf`. All hosts use the
shared [`lxc-docker`](https://github.com/IanCou/Hyades/blob/main/terraform/modules/lxc-docker)
module:

```hcl
module "myservice" {
  source = "../../modules/lxc-docker"

  node_name        = "node1"
  vm_id            = 120
  hostname         = "myservice"
  ip_address       = "10.0.1.42/22"
  gateway          = var.gateway
  template_file_id = var.template_file_id
  ssh_public_key   = var.ssh_public_key
  cores            = 2
  memory           = 2048
  disk_size        = 10
  tags             = ["core", "docker"]
}
```

## 2. Apply with Terraform

Provision just the new module so you don't touch other hosts:

```bash
terraform -chdir=terraform/envs/<tier> apply -target=module.myservice
```

> If you are offline and `.terraform/` is already populated, skip `init` and
> run `apply` directly. Changing an existing LXC's `ip_address` in Terraform is
> a destroy + recreate (data loss); for a running host use the SSH IP-change
> method in `AGENT.md` instead.

## 3. Add the host to the Ansible inventory

Add the host under the correct tier in
[`ansible/inventory/hosts.yml`](https://github.com/IanCou/Hyades/blob/main/ansible/inventory/hosts.yml),
with `service` and `tier` vars so the playbooks can target it:

```yaml
myservice:
  ansible_host: 10.0.1.42 # LXC 120
  service: myservice
  tier: core
```

## 4. Configure the host with Ansible

Run the playbooks in order. `-l <svc>` limits a play to the new host; the
Caddy and Prometheus plays act on shared config so they run unlimited.

```bash
cd ansible
ansible-playbook playbooks/docker.yml -l myservice            # install Docker
ansible-playbook playbooks/deploy.yml -l myservice            # copy compose + up
ansible-playbook playbooks/caddy.yml                          # add proxy route
ansible-playbook playbooks/prometheus.yml                     # re-render scrape targets
ansible-playbook playbooks/authorize-runner.yml -l myservice  # CI runner key
```

What each play does:

| Playbook               | Action                                                                           |
| ---------------------- | -------------------------------------------------------------------------------- |
| `docker.yml`           | Installs Docker Engine on the LXC                                                |
| `deploy.yml`           | Copies the compose stack, runs `docker compose up` ([`docker_compose_v2`][dcv2]) |
| `caddy.yml`            | Builds and deploys Caddy, syncing the whole Caddy directory                      |
| `prometheus.yml`       | Renders scrape targets from inventory, reloads Prometheus                        |
| `authorize-runner.yml` | Authorizes the CI runner's SSH public key                                        |

[dcv2]: https://docs.ansible.com/ansible/latest/collections/community/docker/docker_compose_v2_module.html

The compose stack, Caddy route, and inventory entry must already exist in
the repo before you run these; create them per the
[new service runbook](./new-service.md).

## 5. Add DNS

Add the AdGuard rewrites so the host resolves (see the
[DNS and reverse-proxy runbook](./dns-and-reverse-proxy.md) for the full
procedure):

- `myservice.example.com` → `10.0.1.10` (Caddy) for the web UI.
- `myservice.example.internal` → the LXC IP (`10.0.1.42`) for direct
  access.

With the Terraform module and Caddy route in place, run from `ansible/`:

```bash
ansible-playbook playbooks/adguard-rewrites.yml
```

The playbook derives the rewrites from Terraform and the Caddyfile and updates
AdGuard through its API. It uses `vault_adguard_password`, or you can pass
`-e adguard_password=<pass>`.

## 6. Regenerate docs

Topology changed, so regenerate the `network.md` tables (CI fails if you skip
this):

```bash
make docs
```

## Upstream docs

- [`bpg/proxmox` Terraform provider](https://registry.terraform.io/providers/bpg/proxmox/latest/docs)
- [`community.docker.docker_compose_v2` module](https://docs.ansible.com/ansible/latest/collections/community/docker/docker_compose_v2_module.html)
- [`ansible.builtin` module index](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html)
- [Caddy documentation](https://caddyserver.com/docs/)
