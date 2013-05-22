import bson
import mongoengine
import datetime

class InheritableDocument(mongoengine.Document):
    meta = {
        'abstract': True,
        'allow_inheritance': True,
    }

class InheritableEmbeddedDocument(mongoengine.EmbeddedDocument):
    meta = {
        'abstract': True,
        'allow_inheritance': True,
    }

class Person(InheritableDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)
    hidden = mongoengine.StringField(max_length=200, required=False)

class StrangePerson(Person):
    strange = mongoengine.StringField(max_length=100, required=True)


class Contact(InheritableDocument):
    phone = mongoengine.StringField(max_length=16, required=True)

class Individual(Contact):
    name = mongoengine.StringField(max_length=200, required=True)

class Company(Contact):
    corporate_name = mongoengine.StringField(max_length=200, required=True)

class UnregisteredCompany(Company):
    pass

class ContactGroup(InheritableDocument):
    contacts = mongoengine.ListField(mongoengine.ReferenceField(Contact, required=True))

class EmbeddedPerson(InheritableEmbeddedDocument):
    name = mongoengine.StringField(max_length=200, required=True)
    optional = mongoengine.StringField(max_length=200, required=False)
    hidden = mongoengine.StringField(max_length=200, required=False)

class EmbeddedStrangePerson(EmbeddedPerson):
    strange = mongoengine.StringField(max_length=100, required=True)

class Customer(InheritableDocument):
    person = mongoengine.ReferenceField(Person)
    employed = mongoengine.BooleanField(default=False)

class EmbeddedComment(InheritableEmbeddedDocument):
    content = mongoengine.StringField(max_length=200, required=True)

class EmbeddedPost(InheritableEmbeddedDocument):
    title = mongoengine.StringField(max_length=200, required=True)
    comments = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedComment))

class Board(InheritableDocument):
    posts = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPost))

class EmbeddedCommentWithID(InheritableEmbeddedDocument):
    id = mongoengine.ObjectIdField(primary_key=True, default=lambda: bson.ObjectId())
    content = mongoengine.StringField(max_length=200, required=True)

class DocumentWithID(InheritableDocument):
    title = mongoengine.StringField(max_length=200, required=True)
    comments = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedCommentWithID))

class EmbeddedListInEmbeddedDocTest(InheritableDocument):
    post = mongoengine.EmbeddedDocumentField(EmbeddedPost)

class EmbeddedDocumentFieldTest(InheritableDocument):
    customer = mongoengine.EmbeddedDocumentField(EmbeddedPerson)

class DictFieldTest(InheritableDocument):
    dictionary = mongoengine.DictField(required=True)

class ListFieldTest(InheritableDocument):
    stringlist = mongoengine.ListField(mongoengine.StringField())
    intlist = mongoengine.ListField(mongoengine.IntField())
    anytype = mongoengine.ListField()

class EmbeddedListFieldTest(InheritableDocument):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))

class ReferencedListFieldTest(InheritableDocument):
    referencedlist = mongoengine.ListField(mongoengine.ReferenceField(Person))

class BooleanMapTest(InheritableDocument):
    is_published_auto = mongoengine.BooleanField(default=False, required=True)
    is_published_defined = mongoengine.BooleanField(default=False, required=True)

class EmbeddedListWithFlagFieldTest(InheritableDocument):
    embeddedlist = mongoengine.ListField(mongoengine.EmbeddedDocumentField(EmbeddedPerson))
    is_published = mongoengine.BooleanField(default=False, required=True)

class AutoAllocationFieldTest(InheritableDocument):
    name = mongoengine.StringField(required=True)
    slug = mongoengine.StringField(required=True)

    def save(self, *args, **kwargs):
        from django.template.defaultfilters import slugify
        if not self.slug:
            self.slug = slugify(self.name)
        super(AutoAllocationFieldTest, self).save(*args, **kwargs)

class Exporter(InheritableDocument):
    name = mongoengine.StringField(required=True)

class PipeExporterEmbedded(InheritableEmbeddedDocument):
    name = mongoengine.StringField(required=True)
    exporter = mongoengine.ReferenceField(Exporter, required=True)

class Pipe(InheritableDocument):
    name = mongoengine.StringField(required=True, unique=True)
    exporters = mongoengine.ListField(mongoengine.EmbeddedDocumentField(PipeExporterEmbedded))

class BlankableEmbedded(InheritableEmbeddedDocument):
    name = mongoengine.StringField(required=True, default='A blank name')
    description = mongoengine.StringField()

class BlankableParent(InheritableDocument):
    embedded = mongoengine.EmbeddedDocumentField(BlankableEmbedded, required=True, default=lambda: BlankableEmbedded())

class TimezonedDateTime(InheritableEmbeddedDocument):
    dt = mongoengine.DateTimeField(required=True)
    tz = mongoengine.StringField(required=True)

class ReadonlyParent(InheritableDocument):
    name = mongoengine.StringField(required=True)
    tzdt = mongoengine.EmbeddedDocumentField(TimezonedDateTime, required=True, default=lambda: TimezonedDateTime(dt=datetime.datetime(2012, 12, 12, 12, 12, 12), tz='UTC'))

class DatetimeFieldTest(InheritableDocument):
    datetime = mongoengine.DateTimeField(required=True)
