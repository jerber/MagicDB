from datetime import datetime
from magicdb.Models import MagicModel


class DateModel(MagicModel):
	created_at: datetime
	last_updated: datetime

	def save(self, created_at=None, last_updated=None, *args, **kwargs):
		if not self.created_at: self.created_at = created_at or datetime.utcnow()
		self.last_updated = last_updated or datetime.utcnow()
		return super().save(*args, **kwargs)

	def update(self, last_updated=None, *args, **kwargs):
		self.last_updated = last_updated or datetime.utcnow()
		return super().update(*args, **kwargs)
