PY ?= python3

.PHONY: all figures tables verify clean

all:
	$(PY) src/make_all.py

figures:
	$(PY) src/fig07_static_baselines.py
	$(PY) src/fig08_saving_under_drift.py
	$(PY) src/fig09_rank_inversions.py
	$(PY) src/fig10_reprofiling_cost.py
	$(PY) src/fig11_budget_adherence.py
	$(PY) src/fig12_staleness_robustness.py
	$(PY) src/fig13_sensitivity.py

tables:
	$(PY) src/make_tables.py

verify:
	$(PY) src/verify.py -v

clean:
	rm -f figures/*.pdf figures/*.png tables/*.tex
	rm -rf src/__pycache__
