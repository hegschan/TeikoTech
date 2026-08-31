.PHONY: setup pipeline dashboard

setup:
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt

pipeline:
	MPLBACKEND=Agg python3 load_data.py
	MPLBACKEND=Agg python3 analysis.py

dashboard:
	python3 dashboard.py
