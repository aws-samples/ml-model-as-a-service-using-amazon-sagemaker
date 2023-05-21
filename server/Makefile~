SHELL = /bin/bash -c
VIRTUAL_ENV = $(PWD)/.venv
export BASH_ENV=$(VIRTUAL_ENV)/bin/activate

$(VIRTUAL_ENV):
    python3 -m venv $(VIRTUAL_ENV)

.PHONY: install clean synth diff deploy test lint

install: $(VIRTUAL_ENV)
	pip install -r requirements.txt

clean:
    [[ -d $(VIRTUAL_ENV) ]] && rm -rf $(VIRTUAL_ENV) || true
    [[ -d .pytest_cache ]] && rm -rf .pytest_cache || true
    [[ -d cdk.out ]] && rm -rf cdk.out || true
    [[ -f .coverage ]] && rm .coverage || true

synth:
	cdk synth

diff:
	cdk diff

deploy:
	cdk deploy

destroy:
	cdk destroy -all
	aws cloudformation delete-stack --stack-name mlaas 

test:
	python -cov --cov-report term-mission

lint:
	black .

$(VERBOSE).SILENT: