.PHONY: test audit watch serve deploy clean

PYTHONPATH := src

test:
	PYTHONPATH=$(PYTHONPATH) python3 -m unittest discover -s tests -p "test_*.py" -v

audit:
	PYTHONPATH=$(PYTHONPATH) python3 -m mykairn_sciwatch audit --profile trail_running_coaching

watch:
	PYTHONPATH=$(PYTHONPATH) python3 -m mykairn_sciwatch watch --profile trail_running_coaching --days 30

serve:
	PYTHONPATH=$(PYTHONPATH) python3 -m mykairn_sciwatch serve --host 0.0.0.0 --port 8095

deploy:
	python3 scripts/deploy_freebox_vm.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
