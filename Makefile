.PHONY: docs docs-check lint format verify plan push-secret new-service

docs: ## Regenerate machine-derived tables in docusaurus/docs/network.md
	python3 scripts/gen_docs.py

verify: ## Smoke-test a deployed service (usage: make verify service=<name> [url=https://...])
	@cd ansible && vpf="$${ANSIBLE_VAULT_PASSWORD_FILE:-$$(mktemp)}"; [ -s "$$vpf" ] || printf x >"$$vpf"; \
		ANSIBLE_VAULT_PASSWORD_FILE="$$vpf" \
		ansible-playbook playbooks/verify.yml -l $(service) $(if $(url),-e url=$(url),)

plan: ## Dry-run a deploy: show what would change without applying (usage: make plan service=<name>)
	@cd ansible && vpf="$${ANSIBLE_VAULT_PASSWORD_FILE:-$$(mktemp)}"; [ -s "$$vpf" ] || printf x >"$$vpf"; \
		export ANSIBLE_VAULT_PASSWORD_FILE="$$vpf"; \
		if [ -f "playbooks/$(service).yml" ]; then pb="playbooks/$(service).yml"; args=""; \
		else pb="playbooks/deploy.yml"; args="-l $(service)"; fi; \
		ansible-playbook "$$pb" $$args --check --diff

push-secret: ## Copy a service's local .env to the CI runner (usage: make push-secret service=<name>)
	@cd ansible && vpf="$${ANSIBLE_VAULT_PASSWORD_FILE:-$$(mktemp)}"; [ -s "$$vpf" ] || printf x >"$$vpf"; \
		ANSIBLE_VAULT_PASSWORD_FILE="$$vpf" \
		ansible-playbook playbooks/push-secret.yml -e service=$(service)

new-service: ## Scaffold a new service: make new-service name=X tier=Y node=Z
	python3 scripts/new_service.py $(name) $(tier) $(node)

docs-check: ## Fail if the generated doc tables are out of date
	python3 scripts/gen_docs.py --check

lint: ## Run all formatting/style checks (matches the lint CI workflow)
	npx --yes prettier --check "**/*.{md,yml,yaml,json,js}"
	npx --yes markdownlint-cli2 "**/*.md" "!**/node_modules/**" "!**/.terraform/**" "!**/build/**" "!**/.claude/**" "!services/**" "!ansible/**" "!docusaurus/docs/network.md"

format: ## Auto-fix formatting in place (prettier owns formatting; run once to baseline)
	npx --yes prettier --write "**/*.{md,yml,yaml,json,js}"
