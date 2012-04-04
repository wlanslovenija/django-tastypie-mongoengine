from mongoengine import *

class Person(Document):
    name = StringField(max_length=200, required=True)

class EmbeddedPerson(EmbeddedDocument):
    name = StringField(max_length=200, required=True)
    
class Customer(Document):
    person = ReferenceField(Person)

class EmbededDocumentFieldTest(Document):
    customer = EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(Document):
    dictionary = DictField()

class ListFieldTest(Document):
    stringlist = ListField(StringField())
    intlist = ListField(IntField())

class EmbeddedListFieldTest(Document):
    """
    A document with lists of embedded objects
    """
    
    embeddedlist = SortedListField(EmbeddedDocumentField(EmbeddedPerson))