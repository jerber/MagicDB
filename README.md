# MagicDB
The easiest way to store data.

## Instalation
```
pip install magicdb
```

## Example
```python
from magicdb.Models import MagicModel

class Salesman(MagicModel):
    name: str = None
    company: str = None

s = Salesman()
s.name = 'Jim'
s.save()

# Get Salesman
s = Salesman.collection.get(s.id)
print(s.name) # Jim
```

## Fields
Use any type [mypy](http://mypy-lang.org/) will accept!

#### Fields Example
```python
from datetime import datetime

class Manager(MagicModel):
	name: str
	age: int
	company: str = 'Dunder Mifflin'
	startedWorkingAt: datetime = None

m = Manager(name='Michael Scott')  # you can pass in fields or set them later
m.age = 45
m.save()  # Success! New doc in collection "manager" as: { name: Michael Scott, age: 45, company: Dunder Mifflin }

m = Manager()
m.name = 'Dwight Schrute'
print(m.save())  # Exception since age is required but not given

```

You can also add other Objects as a field.

### NestedModel Example
```python
class Dog(MagicModel):
	age: int
	owner: Manager

dog = Dog()
dog.age = 3
dog.owner = Manager(name='Robert California', age=59)
dog.save()
print(dog)

```


## Collections
The collection name for a class defaults to the class' name in lowercase. To set the collection name, use the `Meta` class.

### Meta Example

```python
class Student(MagicModel):
	name: str = None
	school: str = 'UPenn'

	class Meta:
		collection_name = 'students'


s = Student(name='Amy Gutman')
s.save()  # creates a new document in the "students" collection
print(s)  # name='Amy Gutman' school='UPenn'
```

You can also inheret classes.

### Inheritance Example
```python
class ExchangeStudent(Student):
	originalCountry: str

	class Meta:
		collection_name = 'exchangeStudents'

e = ExchangeStudent(originalCountry='UK')
print(e.school)  # UPenn
e.save()
print(e)  # name=None school='UPenn' originalCountry='UK'
```

## Queries
You can make queries with the same syntax you would using the Python firebase-admin SDK. But FireORM returns the objects.

### Queries Example
```python

e = ExchangeStudent(originalCountry='UK')
print(e.school)  # UPenn
e.save()
print(e)  # name=None school='UPenn' originalCountry='UK'

managers = Manager.collection.where('name', '==', 'Michael Scott').limit(1).stream()
print(managers) # [Manager(name='Michael Scott', age=45, company='Dunder Mifflin', startedWorkingAt=None)]
print(managers[0].id)
manager = Manager.collection.get('0mIWZ8FfgQzBanCllqsV')
print(manager) # name='Michael Scott' age=45 company='Dunder Mifflin' startedWorkingAt=None
```
