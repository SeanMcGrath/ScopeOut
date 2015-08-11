"""
ScopeUtils Test
================

Test the functionality of scopeUtils.
"""
import sys
import unittest as ut
import visa
import os

sys.path.append(os.path.abspath('../../'))
import lib.scopeUtils
import lib.oscilloscopes

def checkUSB():
	try:
		visa.ResourceManager().list_resources("USB?*")
	except:
		return False

	return True

class ScopeFinderTest(ut.TestCase):

	usbCon = checkUSB()

	def setUp(self):
		self.sf = lib.scopeUtils.ScopeFinder()

	def test_getScopes(self):
		self.assertEqual(self.sf.getScopes(), [])

	@ut.skipIf(usbCon == False, "No USB Devices detected")
	def test_refresh(self):
		self.sf.refresh()
		scopes = self.sf.getScopes()
		self.assertTrue(len(scopes) > 0)
		self.assertTrue(isinstance(scopes[0],lib.oscilloscopes.GenericOscilloscope))
	
	@ut.skipIf(usbCon == False, "No USB Devices detected")
	def test_query(self):
		self.sf.refresh()
		scopes = self.sf.getScopes()
		self.assertTrue(isinstance(scopes[0].query('*IDN?'),str))

	@ut.skipIf(usbCon == False, "No USB Devices detected")
	def test_query(self):
		self.sf.refresh()
		scopes = self.sf.getScopes()
		self.assertTrue(isinstance(scopes[0].query('*IDN?'),str))

	@ut.skipIf(usbCon == False, "No USB Devices detected")
	def test_checkScope(self):
		self.sf.refresh()
		scopes = self.sf.getScopes()
		for i in range(0,len(scopes)):
			self.assertTrue(self.sf.checkScope(i))


if __name__ == '__main__':
    ut.main()
