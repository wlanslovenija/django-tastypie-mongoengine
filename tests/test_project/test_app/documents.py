import mongoengine

class Person(mongoengine.Document):
    meta = {
        'allow_inheritance': True,
    }

    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)

class StrangePerson(Person):
    strange = mongoengine.StringField(max_length=100, required=True)

class EmbeddedPerson(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)
    
class Customer(mongoengine.Document):
    person = mongoengine.ReferenceField(Person)

class EmbeddedDocumentFieldTest(mongoengine.Document):
    customer = mongoengine.EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(mongoengine.Document):
    dictionary = mongoengine.DictField(required=True)

class ListFieldTest(mongoengine.Document):
    stringlist = mongoengine.ListField(mongoengine.StringField())
    intlist = mongoengine.ListField(mongoengine.IntField())

class EmbeddedListFieldTest(mongoengine.Document):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))
