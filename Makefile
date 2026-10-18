.PHONY: all data warehouse notebooks clean

all: data warehouse notebooks

data:        ## 1. generate synthetic experiment + journey data (deterministic, seed 42)
	python src/generate_data.py

warehouse:   ## 2. create schema, load CSVs, run sql/*_queries.sql -> data/processed/
	python src/build_warehouse.py

notebooks:   ## 3. execute both notebooks in place (figures + results/*.json)
	jupyter nbconvert --to notebook --execute --inplace notebooks/01_ab_test_analysis.ipynb
	jupyter nbconvert --to notebook --execute --inplace notebooks/02_attribution_modeling.ipynb

clean:
	rm -rf data/raw data/processed data/warehouse.duckdb
