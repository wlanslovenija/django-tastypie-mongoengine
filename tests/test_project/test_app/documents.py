import bson
import mongoengine
import datetime

class Person(mongoengine.Document):
    meta = {
        'allow_inheritance': True,
    }

    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)
    hidden = mongoengine.StringField(max_length=200, required=False)

class StrangePerson(Person):
    strange = mongoengine.StringField(max_length=100, required=True)


class Contact(mongoengine.Document):
    meta = {
        'allow_inheritance': True,
    }

    phone = mongoengine.StringField(max_length=16, required=True)

class Individual(Contact):
    name = mongoengine.StringField(max_length=200, required=True)

class Company(Contact):
    corporate_name = mongoengine.StringField(max_length=200, required=True)

class UnregisteredCompany(Company):
    pass

class ContactGroup(mongoengine.Document):
    contacts = mongoengine.ListField(mongoengine.ReferenceField(Contact, required=True))

class EmbeddedPerson(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)
    hidden = mongoengine.StringField(max_length=200, required=False)

class EmbeddedStrangePerson(EmbeddedPerson):
    strange = mongoengine.StringField(max_length=100, required=True)

class Customer(mongoengine.Document):
    person = mongoengine.ReferenceField(Person)
    employed = mongoengine.BooleanField(default=False)

class EmbeddedComment(mongoengine.EmbeddedDocument):
    content = mongoengine.StringField(max_length=200, required=True)

class EmbeddedPost(mongoengine.EmbeddedDocument):
    title = mongoengine.StringField(max_length=200, required=True)
    comments = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedComment))

class Board(mongoengine.Document):
    posts = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPost))

class EmbeddedCommentWithID(mongoengine.EmbeddedDocument):
    id = mongoengine.ObjectIdField(primary_key=True, default=lambda: bson.ObjectId())
    content = mongoengine.StringField(max_length=200, required=True)

class DocumentWithID(mongoengine.Document):
    title = mongoengine.StringField(max_length=200, required=True)
    comments = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedCommentWithID))

class EmbeddedListInEmbeddedDocTest(mongoengine.Document):
    post = mongoengine.EmbeddedDocumentField(EmbeddedPost)

class EmbeddedDocumentFieldTest(mongoengine.Document):
    customer = mongoengine.EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(mongoengine.Document):
    dictionary = mongoengine.DictField(required=True)

class ListFieldTest(mongoengine.Document):
    stringlist = mongoengine.ListField(mongoengine.StringField())
    intlist = mongoengine.ListField(mongoengine.IntField())
    anytype = mongoengine.ListField()

class EmbeddedListFieldTest(mongoengine.Document):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))

class ReferencedListFieldTest(mongoengine.Document):
    referencedlist = mongoengine.ListField(mongoengine.ReferenceField(Person))

class BooleanMapTest(mongoengine.Document):
    is_published_auto = mongoengine.BooleanField(default=False, required=True)
    is_published_defined = mongoengine.BooleanField(default=False, required=True)

class EmbeddedListWithFlagFieldTest(mongoengine.Document):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))
    is_published = mongoengine.BooleanField(default=False, required=True)

class AutoAllocationFieldTest(mongoengine.Document):
    name = mongoengine.StringField(required=True)
    slug = mongoengine.StringField(required=True)

    def save(self, *args, **kwargs):
        from django.template.defaultfilters import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super(AutoAllocationFieldTest, self).save(*args, **kwargs)

class Exporter(mongoengine.Document):
    name = mongoengine.StringField(required=True)

class PipeExporterEmbedded(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(required=True)
    exporter = mongoengine.ReferenceField(Exporter, required=True)

class Pipe(mongoengine.Document):
    name = mongoengine.StringField(required=True, unique=True)
    exporters = mongoengine.ListField(mongoengine.EmbeddedDocumentField(PipeExporterEmbedded))

class BlankableEmbedded(mongoengine.EmbeddedDocument):
    name = mongoengine.StringField(required=True, default='A blank name')
    description = mongoengine.StringField()

class BlankableParent(mongoengine.Document):
    embedded = mongoengine.EmbeddedDocumentField(BlankableEmbedded, required=True, default=BlankableEmbedded())

class TimezonedDateTime(mongoengine.EmbeddedDocument):
    dt = mongoengine.DateTimeField(required=True)
    tz = mongoengine.StringField(required=True)

class ReadonlyParent(mongoengine.Document):
    name = mongoengine.StringField(required=True)
    tzdt = mongoengine.EmbeddedDocumentField(TimezonedDateTime, required=True, default=TimezonedDateTime(dt=datetime.datetime(2012, 12, 12, 12, 12, 12), tz='UTC'))
