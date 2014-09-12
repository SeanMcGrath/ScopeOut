from scopeFinder import ScopeFinder

scopes = ScopeFinder().getScopes()
if scopes:
	TDS = scopes[0]
	print(TDS.query("*IDN?"))