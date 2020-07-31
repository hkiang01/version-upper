coverage:
	# generates coverage report used by Coverage Gutters extension
	py.test . --cov-report xml:cov.xml --cov .