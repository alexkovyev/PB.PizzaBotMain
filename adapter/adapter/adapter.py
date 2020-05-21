import DBBridge

class STFF_Adapter:
	def select_AllHalfstuff(self):
		#type = adapterData.type
		#debugOutput = adapterData.debugOutput
		# here you can return result (function execute return result)
		data = DBBridge.execute(self, 'FN_OpenPackage', ['B2_D4'])
		# data is a list of coratges (1 cortage is a row. Order is import)

STFF_Adapter.select_AllHalfstuff()