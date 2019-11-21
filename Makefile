SRC = $(PWD)/src
TESTS = $(PWD)/tests

AWS_PROFILE = default
CHALICE = cd $(SRC); chalice
DATA_STACK_NAME = task-888-data-pipeline
PYTHON = python3
REQUIREMENTS = $(SRC)/requirements.txt
STAGE = dev

.PHONY: unit test coverage deploy clean delete tdd

deps: .deps
.deps: $(REQUIREMENTS) requirements.txt
	pip install -r requirements.txt
	pip install -r $(REQUIREMENTS)
	touch .deps

cfn/api.json: src/app.py deps
	$(CHALICE) package \
		--stage $(STAGE) \
		../_temp
	mv _temp/sam.json cfn/api.json

deploy_api: deps cfn/api.json
	$(CHALICE) deploy \
		--no-autogen-policy \
		--profile $(AWS_PROFILE) \
		--stage $(STAGE)

delete: deps
	$(CHALICE) delete \
		--profile $(AWS_PROFILE) \
		--stage $(STAGE)

clean:
	@echo "Cleaning all artifacts..."
	@-rm -rf _build
	@-rm -rf _temp
	@-rm .deps

url: deps
	@$(CHALICE) url --stage $(STAGE)

list:
	cat $(SRC)/.chalice/deployed/*.json

ipython: deps
	cd $(SRC);\
	$(PYTHON) -m IPython

run: deps
	$(CHALICE) local --autoreload --port 8887

unit test: deps
	cd $(SRC);\
	$(PYTHON) -m pytest ../tests

tdd: deps
	cd $(SRC);\
	$(PYTHON) -m pytest --stepwise $(TESTS)

debug: deps
	cd $(SRC);\
	$(PYTHON) -m pytest --stepwise -vv --pdb $(TESTS)

coverage: deps
	cd $(SRC);\
	$(PYTHON) -m pytest ../tests --cov $(SRC) --cov-report=term-missing ../tests

validate_data:
	@aws cloudformation validate-template \
		--template-body file://cfn/data.yaml

deploy_data:
	make deploy_data_silent || make explain_data

deploy_data_silent: validate_data
	@aws cloudformation deploy \
		--capabilities CAPABILITY_IAM \
		--no-fail-on-empty-changeset \
		--parameter-overrides \
			Environment=$(STAGE) \
		--stack-name "$(DATA_STACK_NAME)-$(STAGE)" \
		--template-file cfn/data.yaml

explain_data:
	@aws cloudformation describe-stack-events \
		--stack-name "$(DATA_STACK_NAME)-$(STAGE)" > .cf.messages
	@python .cf_status.py | ccze -A

deploy:
	make deploy_api
	# make deploy_data
