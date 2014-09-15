from scopeFinder import ScopeFinder

print("Initializing...")

scopes = ScopeFinder().getScopes()
if scopes:
	TDS = scopes[0]

	print('{:s} {:s} Oscilloscope REPL'.format(TDS.make,TDS.model))
	print("Enter command:")
	print()

	running = True
	while running:
		print(">>",end='')
		
		command = input()
		
		if command == "exit":
			running = False
		elif command == "read":
			print(TDS.read())
		elif command == "ID":
			print(TDS)
		elif command == "getWave":
			print(TDS.getWaveform())
		elif command == "curve":
			print(TDS.getCurve())
		elif command == "plot":
			TDS.plotCurve()
		
		else:
			TDS.write(command)
			if command[-1] == "?":
				print(TDS.read())