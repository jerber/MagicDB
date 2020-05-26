import time
import pprint
import copy
from typing import Dict
from pydantic import BaseModel
from pydantic.fields import ModelField
from pydantic.main import ModelMetaclass
from magicdb.Queries import Query
from magicdb import db
from magicdb.utils import make_update_obj


class DatabaseError(Exception):
	def __init__(self, key):
		self.message = \
			f'There is no document with key {key} to update. Add update.(create=True) to save the document' \
			f' if it does not exist. Otherwise, you can save the document: save().'


class QueryMeta(type):
	"""https://stackoverflow.com/questions/128573/using-property-on-classmethods"""

	@property
	def collection(cls):
		return Query(cls)

	@property
	def collection_group(cls):
		return Query(cls).collection_group()


class QueryAndBaseMetaClasses(ModelMetaclass, QueryMeta):
	pass


class MagicModel(BaseModel, metaclass=QueryAndBaseMetaClasses):
	"""Class that wraps BaseModel, giving Firestore functionality and field forgiveness"""

	def __init__(self, from_db=False, forgiveness=None, **kwargs):
		if forgiveness is None:
			forgiveness = from_db

		self.set_db_fields(kwargs, from_db)
		self.add_init_forgiveness(**kwargs) if forgiveness else BaseModel.__init__(self, **kwargs)

	def set_db_fields(self, kwargs, from_db=False):
		self.db_fields.id = kwargs.get('id')
		self.db_fields.key = kwargs.get('key')
		self.db_fields.parent = kwargs.get('parent')
		self.db_fields.ref = kwargs.get('ref')
		self.db_fields.kwargs_from_db = kwargs if from_db else {}
		self.make_db_fields()

	def add_init_forgiveness(self, **kwargs):
		fields: Dict[str, ModelField] = self.__class__.__fields__
		model_fields_changed: list = []
		for model_field in fields.values():
			if model_field.name not in kwargs and getattr(model_field, 'required', False):
				model_fields_changed.append(model_field)
				model_field.required = False

		BaseModel.__init__(self, **kwargs)

		for model_field in model_fields_changed:
			model_field.required = True

	def validate_py(self):
		"""Validates but also adds None for the removed fields.
		The first init validates all current info and adds None to fields that were del
		The second init validates all the None fields to make sure they can be None."""
		BaseModel.__init__(self, **self.dict())
		BaseModel.__init__(self, **self.dict())

	def __eq__(self, other):
		return self.__class__ == other.__class__ and self.__dict__ == other.__dict__

	"""CREATE META FIELDS"""

	def make_db_fields(self):
		"""Will make db_fields information either from key, ref, or id (included no id given or parent given).
		Whichever one exists, in that order."""
		if getattr(self.db_fields, 'key', None):
			self.make_db_fields_from_key()
		elif getattr(self.db_fields, 'ref', None):
			self.make_db_fields_from_ref()
		else:
			self.make_db_fields_from_id()

	def make_db_fields_from_key(self):
		self.db_fields.ref = db.conn.document(self.db_fields.key)
		self.db_fields.id = self.id_from_key(self.db_fields.key)

	def make_db_fields_from_ref(self):
		self.db_fields.key = self.key_from_ref(self.db_fields.ref)
		self.db_fields.id = self.id_from_key(self.db_fields.key)

	def make_db_fields_from_id(self):
		"""Assigns db_fields fields using an id if given. Otherwise, makes an id... Also uses parent if necessary."""
		collection_name = self.get_collection_name()
		collection_ref = db.conn.collection(
			collection_name) if not self.db_fields.parent else self.db_fields.parent.ref.collection(
			collection_name)
		self.db_fields.ref = collection_ref.document() if not self.db_fields.id else collection_ref.document(
			self.db_fields.id)
		self.make_db_fields_from_ref()

	"""COLLECTION CLASS FUNCTIONS"""

	@classmethod
	def make_collection_name(cls):
		return cls.__name__.lower()

	@classmethod
	def get_collection_name(cls):
		return getattr(getattr(cls, 'Meta', None), 'collection_name', cls.make_collection_name())

	"""HELPER STATIC FUNCTIONS"""

	@staticmethod
	def key_from_ref(ref):
		return '/'.join(ref._path)

	@staticmethod
	def id_from_key(key):
		return key[key.rindex('/') + 1:]

	"""GETTERS AND SETTERS FOR META FIELDS"""

	@property
	def db_fields(self):
		meta = getattr(self.__class__, 'Meta', None)

		class Instance:
			pass

		if not meta:
			class Meta:
				pass
			self.__class__.Meta = Meta
			meta = self.__class__.Meta

		if not hasattr(meta, 'instances'): meta.instances: Dict[int: Instance] = {}
		if id(self) not in meta.instances: meta.instances[id(self)] = Instance()
		return meta.instances[id(self)]

	@property
	def id(self):
		return self.db_fields.id

	@id.setter
	def id(self, id):
		self.db_fields.id = id
		self.make_db_fields_from_id()

	@property
	def key(self):
		return self.db_fields.key

	@key.setter
	def key(self, key):
		self.db_fields.key = key
		self.make_db_fields_from_key()

	@property
	def parent(self):
		return self.db_fields.parent

	@parent.setter
	def parent(self, parent):
		self.db_fields.parent = parent
		self.make_db_fields_from_id()

	@property
	def ref(self):
		return self.db_fields.ref

	@ref.setter
	def ref(self, ref):
		self.db_fields.ref = ref
		self.make_db_fields_from_ref()

	"""ADDING TO FIRESTORE"""

	def save(self, batch=None, merge=False, ignore_fields=False):
		"""Saves object to firestore"""
		# validate_py update the internal dict to make all deleted fields are None and validates all fields
		if not ignore_fields: self.validate_py()
		new_d = self.dict()
		self.db_fields.ref.set(new_d, merge=merge) if not batch else batch.set(self.db_fields.ref, new_d, merge=merge)
		if not merge: self.db_fields.kwargs_from_db = copy.deepcopy(new_d)
		return self

	def update(self, batch=None, create=False, ignore_fields=False):
		if not ignore_fields: self.validate_py()
		new_d = self.dict()
		update_d = new_d if not self.db_fields.kwargs_from_db else make_update_obj(
			original=self.db_fields.kwargs_from_db, new=new_d
		)

		try:
			self.db_fields.ref.update(update_d) if not batch else batch.update(self.db_fields.ref, update_d)
			return self
		except Exception as e:
			if hasattr(e, 'message') and 'no document to update' in e.message.lower():
				if create:
					return self.save(batch=batch)
				else:
					db_error = DatabaseError(self.db_fields.key)
					raise DatabaseError(db_error.message)

	def delete(self, batch=None):
		return self.db_fields.ref.delete() if not batch else batch.delete(self.db_fields.ref)

	"""QUERYING AND COLLECTIONS"""

	@classmethod
	def get_collection(cls):
		return cls.collection

	def get_subcollections(self):
		return list(self.get_collection().document(self.id).collections())

	"""GETTING SUBCOLLECTIONS"""

	@classmethod
	def get_subclasses(cls):
		all_subs = []
		for sub in cls.__subclasses__():
			all_subs.append(sub)
			all_subs += sub.get_subclasses()
		return list(set(all_subs))

	@staticmethod
	def get_all_subclasses_of_model():
		all_subs = []
		for sub in list(MagicModel.__subclasses__()):
			all_subs.append(sub)
			all_subs += sub.get_subclasses()
		return list(set(all_subs))
