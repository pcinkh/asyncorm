from asyncorm.application import get_model
from asyncorm.exceptions import *
from asyncorm.fields import *
from asyncorm.serializers import ModelSerializer, SerializerMethod

from .testapp.models import Book, Author
from .testapp.serializer import BookSerializer, BookSerializer2
from .testapp2.models import Developer, Client, Organization
from .test_helper import AioTestCase

# You can get the book by model_name
Book2 = get_model('Book')
# And get the author by module.model_name
Author2 = get_model('testapp.Author')


class ModelTests(AioTestCase):

    def test_class__init__(self):
        # classmethods tests
        # no matter how you import them they are the same object
        self.assertTrue(Author is Author2)
        self.assertTrue(Book is Book2)

        self.assertEqual(Book().cls_tablename(), 'library')
        self.assertEqual(Author().cls_tablename(), 'Author')

        fields = Book.get_fields()

        self.assertEqual(len(fields), 7)
        self.assertEqual(
            sorted(list(fields.keys())),
            sorted(
                ['id', 'content', 'name', 'author', 'date_created', 'price',
                 'quantity']
            )
        )

        fields = Author.get_fields()

        self.assertEqual(len(fields), 5)
        self.assertEqual(
            sorted(list(fields.keys())),
            sorted(['na', 'name', 'age', 'publisher', 'email'])
        )

    def test_instantiated__init__(self):
        # classmethods tests
        book = Book()

        self.assertEqual(book.db_pk, 'id')
        self.assertEqual(book.orm_pk, 'id')

        author = Author()

        self.assertEqual(author.db_pk, 'uid')
        self.assertEqual(author.orm_pk, 'na')

    def test_validate_kwargs(self):
        kwargs = {
            'name': 67,
        }

        # raises the validate content has an incorrect value
        with self.assertRaises(FieldError) as exc:
            book = Book()
            book.validate_kwargs(kwargs)
        self.assertTrue(
            'is a wrong datatype for field' in exc.exception.args[0]
        )

        kwargs = {
            'id': 34,
            'name': 'name',
        }

        # also raises fielderror because you can not pre-set the object's id
        with self.assertRaises(FieldError) as exc:
            book = Book()
            book.validate_kwargs(kwargs)
        self.assertEqual(
            exc.exception.args[0],
            'Models can not be generated with forced id'
        )

        kwargs.pop('id')

        kwargs['volume'] = 23
        # raises the validate error because volume is not a correct attrib
        with self.assertRaises(ModelError) as exc:
            book = Book()
            book.validate_kwargs(kwargs)
        # its a list because we validate all kwargs
        self.assertEqual(
            exc.exception.args[0],
            ['"volume" is not an attribute for Book', ]
        )

        kwargs.pop('volume')

        # now it correctly validates
        book.validate_kwargs(kwargs)

    async def test_ordering(self):
        self.assertEqual(Book().ordering, ['-id'])
        self.assertEqual(Author().ordering, None)

        q_books = Book.objects.filter(id__lt=10)
        async for book in q_books:
            self.assertEqual(book.id, 9)
            break

    async def test_fk(self):
        # the inverse relation is correctly set
        self.assertTrue(hasattr(Developer, 'client_set'))

        # create a developer
        dev = Developer(name='developboy', age=24)
        await dev.save()
        # Assign a boss to it
        client = Client(name='devman', dev=dev.id)
        await client.save()

        # the client has the dev correctly set
        self.assertTrue(client.dev == client.id)

        # and the relation comes back
        # the method exists
        self.assertTrue(hasattr(dev, 'client_set'))
        clients_returned = dev.client_set()

        # and is correct
        async for client in clients_returned:
            self.assertTrue(client.id == dev.id)

    async def test_m2m(self):
        # the inverse relation is correctly set
        self.assertTrue(hasattr(Organization, 'developer_set'))

        # new organization
        org_list = []
        for x in range(1, 6):
            org = Organization(name='ong molona')
            await org.save()
            org_list.append(org.id)

        # create a developer
        dev = Developer(name='developer', age=55, org=org_list)
        await dev.save()

        # and the relation comes back
        # the method exists
        devs_returned = org.developer_set()
        orgs_returned = dev.organization_set()

        # and they are correct
        async for dd in devs_returned:
            self.assertEqual(dd.id, dev.id)
            break

        dev = await Developer.objects.get(name='developer', age=55)
        # the first is 1
        async for dd in orgs_returned:
            self.assertTrue(dd.id in org_list)

    async def test_serialize(self):
        # the inverse relation is correctly set
        q_book = Book.objects.filter(id__lt=100)

        async for book in q_book:

            # meta fields definition is not correct
            with self.assertRaises(SerializerError) as exc:
                BookSerializer().serialize(book)
            self.assertTrue(
                'is not a correct argument for model' in exc.exception.args[0]
            )
            break

        # complains if we try to serialize an incorrect model
        with self.assertRaises(SerializerError) as exc:
            author = Author()
            BookSerializer2().serialize(author)
        self.assertTrue(
            'That model is not an instance of' in exc.exception.args[0]
        )

        serialized_book = BookSerializer2().serialize(book)
        self.assertEqual(serialized_book.get('name'), 'book name 98')

        # complains if we have a model serializer without model
        with self.assertRaises(SerializerError) as exc:

            class NooneSerializer(ModelSerializer):

                class Meta:
                    fields = ['name', 'content', ]
        self.assertEqual(
            'The serializer has to define the model it\'s serializing',
            exc.exception.args[0]
        )

        # complains if we have a model serializer without model
        with self.assertRaises(SerializerError) as exc:

            class Noone2Serializer(ModelSerializer):

                class Meta:
                    model = Book

        self.assertEqual(
            'The serializer has to define the fields\'s to serialize',
            exc.exception.args[0]
        )

        # complains if we have a model serializer without model
        with self.assertRaises(SerializerError) as exc:

            class BookSerializerNew(ModelSerializer):
                its_a_2 = SerializerMethod()

                def get_its_a_2(self, instance):
                    return instance.its_a_2()

                class Meta:
                    model = Book
                    fields = ['its_a_2', 'its_a_3', ]

            BookSerializerNew().serialize(await Book.objects.get(id=3))

        self.assertTrue(
            'its_a_3 is not a correct argument for model' in
            exc.exception.args[0]
        )

        class BookSerializerNew(ModelSerializer):
            its_a_2 = SerializerMethod()

            def get_its_a_2(self, instance):
                return instance.its_a_2()

            class Meta:
                model = Book
                fields = ['its_a_2', ]

        book_ser = BookSerializerNew().serialize(await Book.objects.get(id=3))
        self.assertEqual(book_ser['its_a_2'], 2)
