from django.utils import unittest
from .documents import *

class SimpleTest(unittest.TestCase):
    def setUp(self):
        Person.drop_collection()
        Customer.drop_collection()
        EmbededDocumentFieldTest.drop_collection()
        DictFieldTest.drop_collection()
        ListFieldTest.drop_collection()
        EmbeddedListFieldTest.drop_collection()
        
        p1 = Person(name="Person 1")
        p1.save()
        p2 = Person(name="Person 2")
        p2.save()
        Customer(person=p1).save()
        
        ep1 = EmbeddedPerson(name="Embeded 1")
        ep2 = EmbeddedPerson(name="Embeded 2")
        ep3 = EmbeddedPerson(name="Embeded 3")
        
        EmbededDocumentFieldTest(customer=ep1).save()
        
        DictFieldTest(dictionary={'a': 'abc', 'number': 34}).save()
        
        ListFieldTest(stringlist=('a', 'b', 'c'), intlist=(1, 2, 3)).save()
        
        EmbeddedListFieldTest(embededlist=(ep2, ep1, ep2)).save()
        
        
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)
