import mongoengine

class Person(mongoengine.Document):
    name = mongoengine.StringField(max_length=200, required=True)

class EmbeddedPerson(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    
class Customer(mongoengine.Document):
    person = mongoengine.ReferenceField(Person)

class EmbededDocumentFieldTest(mongoengine.Document):
    customer = mongoengine.EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(mongoengine.Document):
    dictionary = mongoengine.DictField()

class ListFieldTest(mongoengine.Document):
    stringlist = mongoengine.ListField(mongoengine.StringField())
    intlist = mongoengine.ListField(mongoengine.IntField())

class EmbeddedListFieldTest(mongoengine.Document):
    """
    A document with lists of embedded objects
    """
    
    embeddedlist = mongoengine.SortedListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))