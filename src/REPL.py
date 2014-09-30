"""
Rudimentary REPL for interacting with TDS2024B Oscilloscope.
"""

print("Initializing...")

from lib.scopeUtils import ScopeFinder

scopes = ScopeFinder().getScopes()
if scopes:
	TDS = scopes[0]

	print('{:s} {:s} Oscilloscope REPL'.format(TDS.make,TDS.model))
	print("Enter command:")
	print()

	running = True
	while running:
		
		command = input('>>').lower()
		
		if command  in ["exit",'x']:
			running = False
		elif command in ["read", 'r']:
			print(TDS.read())
		elif command == "id":
			print(TDS)
		elif command in ["getwave",'w']:
			print(TDS.getWaveform())
		elif command in ["curve",'c']:
			print(TDS.getCurve())
		elif command in ["plot",'p']:
			TDS.plotCurve()
		elif command in ["trigplot",'tp']:
			print("Waiting for trigger...")
			trig = TDS.checkTrigger()
			while trig != "TRIGGER":
				trig = TDS.checkTrigger()

			print('TRIGGER')
			TDS.plotCurve()

		elif command:
			TDS.write(command)
			if command[-1] == "?":
				print(TDS.read())