import firebase_admin
from firebase_admin import credentials, firestore


class Database:

	def __init__(self):
		self._conn = None

	def connect(self, creds=None, from_file=None, firestore_instance=None):
		if not creds and not from_file and not firestore_instance:
			raise Exception("Credentials, service account json file path, or firestore_instance required to connect with firestore")
		if from_file:
			creds = credentials.Certificate(from_file)
		if creds:
			try:
				firebase_admin.initialize_app(creds)
			except Exception as e:
				if 'The default Firebase app already exists' in str(e) and not firestore_instance:
					raise Exception(
						'If you want to connect to Firestore from_file, make sure fireorm.connect(from_file=<YOUR FILE>) '
						'comes directly after importing FireORM for the first time.')
		if firestore_instance:
			self._conn = firestore_instance
		else:
			self._conn = firestore.client()

	@property
	def conn(self):
		if self._conn is None:
			firebase_admin.initialize_app()
			self._conn = firestore.client()
		return self._conn
