from scopeFinder import ScopeFinder

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
		else:
			TDS.write(command)
			if command[-1] == "?":
				print(TDS.read())