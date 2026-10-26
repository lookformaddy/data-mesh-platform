.PHONY: test demo serve lint

test:
	pytest -q

demo:
	python examples/run_demo.py

serve:
	python -m datamesh serve

lint:
	python -m compileall -q src tests examples
