print("Initializing...")

from scopeFinder import ScopeFinder

scopes = ScopeFinder().getScopes()
if scopes:
	TDS = scopes[0]

	while True:
		print(TDS.query("TRIG:STATE?"))