.PHONY: init migrate worker api web test lint

ENV_FILE := .env

init:
	@if [ ! -f $(ENV_FILE) ]; then \
		KEY=$$(python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"); \
		printf 'DATABASE_URL=postgresql+psycopg://rap:rap@localhost:5432/rap\nSETTINGS_ENCRYPTION_KEY=%s\n' "$$KEY" > $(ENV_FILE); \
		echo "Wrote $(ENV_FILE) with a generated SETTINGS_ENCRYPTION_KEY."; \
	else \
		if ! grep -q '^SETTINGS_ENCRYPTION_KEY=.\+' $(ENV_FILE); then \
			KEY=$$(python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"); \
			if grep -q '^SETTINGS_ENCRYPTION_KEY=' $(ENV_FILE); then \
				sed -i.bak "s|^SETTINGS_ENCRYPTION_KEY=.*|SETTINGS_ENCRYPTION_KEY=$$KEY|" $(ENV_FILE) && rm -f $(ENV_FILE).bak; \
			else \
				printf '\nSETTINGS_ENCRYPTION_KEY=%s\n' "$$KEY" >> $(ENV_FILE); \
			fi; \
			echo "Filled SETTINGS_ENCRYPTION_KEY in $(ENV_FILE)."; \
		else \
			echo "$(ENV_FILE) already has SETTINGS_ENCRYPTION_KEY."; \
		fi; \
		if ! grep -q '^DATABASE_URL=' $(ENV_FILE); then \
			printf 'DATABASE_URL=postgresql+psycopg://rap:rap@localhost:5432/rap\n' >> $(ENV_FILE); \
		fi; \
	fi

migrate:
	. .venv/bin/activate 2>/dev/null || true; \
	alembic upgrade head

worker:
	rap worker

api:
	rap api

test:
	pytest -q

lint:
	ruff check rap tests
	mypy rap
