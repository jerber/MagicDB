from datetime import datetime
from magicdb.Models import MagicModel
from magicdb.utils import make_update_obj


class DateModel(MagicModel):
	created_at: datetime = None
	last_updated: datetime = None

	def save(self, created_at=None, last_updated=None, *args, **kwargs):
		if not self.created_at: self.created_at = created_at or datetime.utcnow()
		self.last_updated = last_updated or datetime.utcnow()
		return super().save(*args, **kwargs)

	def update(self, last_updated=None, *args, **kwargs):
		self.last_updated = last_updated or datetime.utcnow()
		return super().update(*args, **kwargs)

	# TODO not sure if this works so check...
	def dict(self, nested=False, *args, **kwargs):
		d = super().dict()
		if not self.db_fields.kwargs_from_db or not nested: return d  # TODO check to see if this works
		update_d = make_update_obj(self.db_fields.kwargs_from_db, d)
		if not update_d == {} or ('last_updated' in update_d and len(update_d) == 1):
			self.last_updated = update_d.get('last_updated', datetime.utcnow())
			d['last_updated'] = self.last_updated
		return d
