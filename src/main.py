from scopeFinder import ScopeFinder

TDS = ScopeFinder().getScopes()[0]
print(TDS.query("*IDN?"))